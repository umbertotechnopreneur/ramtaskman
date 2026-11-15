"""Experimental Windows VirtualQueryEx metadata; no process contents or estimates.

This initial provider is intentionally limited to virtual regions: region-level
resident/private counters remain unavailable until measured and validated on Windows.
No native DLL is loaded on import, allowing use of other backends on Unix.
"""
from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Callable
import ctypes
import ntpath
import sys
import time

import psutil

from ..models import ProcessMemory
from ..regions import MemoryRegion, RegionSnapshot
from ..region_provider import RegionCapabilities

_COMMIT, _RESERVE, _FREE = 0x1000, 0x2000, 0x10000
_STATES = {_COMMIT: 'MEM_COMMIT', _RESERVE: 'MEM_RESERVE', _FREE: 'MEM_FREE'}
_TYPES = {0x20000: 'MEM_PRIVATE', 0x40000: 'MEM_MAPPED', 0x1000000: 'MEM_IMAGE'}
_PROTECTIONS = {1: 'NOACCESS', 2: 'READONLY', 4: 'READWRITE', 8: 'WRITECOPY',
                0x10: 'EXECUTE', 0x20: 'EXECUTE_READ', 0x40: 'EXECUTE_READWRITE',
                0x80: 'EXECUTE_WRITECOPY'}


@dataclass(frozen=True)
class WinRegion:
    start: int
    size: int
    state: int
    protection: int
    type: int


class _MemoryBasicInformation64(ctypes.Structure):
    # Explicit 64-bit layout, verified against Microsoft's MEMORY_BASIC_INFORMATION64.
    _fields_ = [('BaseAddress', ctypes.c_uint64), ('AllocationBase', ctypes.c_uint64),
                ('AllocationProtect', ctypes.c_uint32), ('alignment1', ctypes.c_uint32),
                ('RegionSize', ctypes.c_uint64), ('State', ctypes.c_uint32),
                ('Protect', ctypes.c_uint32), ('Type', ctypes.c_uint32),
                ('alignment2', ctypes.c_uint32)]


class _SystemInfo(ctypes.Structure):
    _fields_ = [('architecture_union', ctypes.c_uint32), ('page_size', ctypes.c_uint32),
                ('minimum', ctypes.c_void_p), ('maximum', ctypes.c_void_p),
                ('active_mask', ctypes.c_size_t), ('number', ctypes.c_uint32),
                ('type', ctypes.c_uint32), ('allocation_granularity', ctypes.c_uint32),
                ('level', ctypes.c_uint16), ('revision', ctypes.c_uint16)]


class _NativeAPI:
    def __init__(self) -> None:
        if sys.platform != 'win32' or ctypes.sizeof(ctypes.c_void_p) != 8:
            raise OSError('Provider Windows sperimentale richiede Python Windows a 64 bit')
        self.dll = ctypes.WinDLL('kernel32', use_last_error=True)
        self.dll.OpenProcess.argtypes = [ctypes.c_uint32, ctypes.c_int, ctypes.c_uint32]
        self.dll.OpenProcess.restype = ctypes.c_void_p
        self.dll.CloseHandle.argtypes = [ctypes.c_void_p]
        self.dll.CloseHandle.restype = ctypes.c_int
        self.dll.VirtualQueryEx.argtypes = [ctypes.c_void_p, ctypes.c_void_p,
                                            ctypes.POINTER(_MemoryBasicInformation64), ctypes.c_size_t]
        self.dll.VirtualQueryEx.restype = ctypes.c_size_t
        self.dll.GetSystemInfo.argtypes = [ctypes.POINTER(_SystemInfo)]
        self.dll.GetSystemInfo.restype = None

    def limits(self) -> tuple[int, int, int]:
        info = _SystemInfo()
        self.dll.GetSystemInfo(ctypes.byref(info))
        if not info.page_size or info.maximum is None:
            raise OSError('GetSystemInfo non ha fornito limiti utilizzabili')
        return int(info.minimum or 0), int(info.maximum), int(info.page_size)

    def open(self, pid: int):
        handle = self.dll.OpenProcess(0x0400, False, pid)  # PROCESS_QUERY_INFORMATION
        if not handle:
            raise ctypes.WinError(ctypes.get_last_error())
        return handle

    def close(self, handle) -> None:
        self.dll.CloseHandle(handle)

    def query(self, handle, address: int) -> WinRegion:
        info = _MemoryBasicInformation64()
        count = self.dll.VirtualQueryEx(handle, ctypes.c_void_p(address), ctypes.byref(info), ctypes.sizeof(info))
        if count != ctypes.sizeof(info):
            if not count:
                raise ctypes.WinError(ctypes.get_last_error())
            raise OSError('VirtualQueryEx: struttura incompleta')
        return WinRegion(info.BaseAddress, info.RegionSize, info.State, info.Protect, info.Type)


def _verify(process: ProcessMemory) -> str | None:
    current = psutil.Process(process.pid)
    if current.create_time() != process.started_at or not current.is_running():
        raise ProcessLookupError('processo terminato o PID riutilizzato')
    try:
        executable = current.exe()
        return ntpath.normcase(executable) if executable else None
    except (psutil.AccessDenied, PermissionError):
        return None


def _protection(value: int) -> str:
    if not value:
        return 'n/a'
    label = _PROTECTIONS.get(value & 0xff, f'0x{value & 0xff:x}')
    flags = [(0x100, 'GUARD'), (0x200, 'NOCACHE'), (0x400, 'WRITECOMBINE')]
    label += ''.join('|' + name for bit, name in flags if value & bit)
    extra = value & ~(0xff | 0x100 | 0x200 | 0x400)
    return label + (f'|0x{extra:x}' if extra else '')


class WindowsRegionProvider:
    capabilities = RegionCapabilities('windows', 'Windows VirtualQueryEx (sperimentale)', True,
                                      virtual=True, explanation='Residenza per regione non ancora disponibile.')

    def __init__(self, api=None, *, max_regions: int = 32768,
                 max_queries: int = 131072, max_seconds: float = 3.0) -> None:
        if max_regions <= 0 or max_queries <= 0 or max_seconds <= 0:
            raise ValueError('I limiti della scansione devono essere positivi')
        self.api = api
        self.max_regions, self.max_queries, self.max_seconds = max_regions, max_queries, max_seconds

    def read(self, process: ProcessMemory, cancelled: Callable[[], bool] | None = None) -> RegionSnapshot:
        started = time.monotonic()
        snapshot = RegionSnapshot(process.pid, process.started_at, process.name, time.time())
        handle = None
        api = self.api
        try:
            if cancelled and cancelled():
                snapshot.complete, snapshot.reason = False, 'Scansione annullata'
                return snapshot
            before_exe = _verify(process)
            api = api or _NativeAPI()
            low, high, page_size = api.limits()
            if low < 0 or high < low or page_size <= 0:
                raise ValueError('limiti indirizzi o dimensione pagina non validi')
            handle = api.open(process.pid)
            address = low
            queries = 0
            while address <= high:
                if cancelled and cancelled():
                    snapshot.complete, snapshot.reason = False, 'Scansione annullata'
                    break
                if time.monotonic() - started >= self.max_seconds:
                    snapshot.complete, snapshot.reason = False, 'Limite di tempo raggiunto; campione parziale'
                    break
                if queries >= self.max_queries:
                    snapshot.complete, snapshot.reason = False, 'Limite di chiamate raggiunto; campione parziale'
                    break
                entry = api.query(handle, address)
                queries += 1
                end = entry.start + entry.size
                if (entry.start > address or (queries > 1 and entry.start != address)
                        or entry.start < 0 or entry.size <= 0 or end <= address or end > 1 << 64):
                    raise ValueError('intervallo VirtualQueryEx non valido')
                if entry.state not in _STATES:
                    raise ValueError('stato VirtualQueryEx sconosciuto')
                if entry.state != _FREE:
                    if len(snapshot.regions) >= self.max_regions:
                        snapshot.complete, snapshot.reason = False, 'Limite di regioni raggiunto; campione parziale'
                        break
                    state = _STATES[entry.state]
                    typ = _TYPES.get(entry.type, f'TYPE_0x{entry.type:x}')
                    # Reserved regions have undefined Protect per the Windows API.
                    protection = _protection(entry.protection) if entry.state == _COMMIT else 'n/a'
                    snapshot.regions.append(MemoryRegion(entry.start, end, protection,
                        path=f'[{state} · {typ}]', category='special'))
                address = end
            after_exe = _verify(process)
            if before_exe and after_exe and before_exe != after_exe:
                raise ProcessLookupError('immagine eseguibile cambiata')
            snapshot.executable_identity = before_exe if before_exe and before_exe == after_exe else None
            if snapshot.complete and time.monotonic() - started >= self.max_seconds:
                snapshot.complete, snapshot.reason = False, 'Limite di tempo raggiunto; campione parziale'
            if snapshot.complete and cancelled and cancelled():
                snapshot.complete, snapshot.reason = False, 'Scansione annullata'
        except (PermissionError, psutil.AccessDenied):
            snapshot.complete, snapshot.reason = False, 'VirtualQueryEx: accesso negato'
            snapshot.regions.clear()
        except (psutil.NoSuchProcess, ProcessLookupError):
            snapshot.complete, snapshot.reason = False, 'Processo terminato o PID riutilizzato'
            snapshot.regions.clear()
        except (OSError, ValueError, psutil.Error) as error:
            snapshot.complete, snapshot.reason = False, f'VirtualQueryEx: {error}'
            snapshot.regions.clear()
        finally:
            if handle is not None and api is not None:
                api.close(handle)
            snapshot.sample_ms = (time.monotonic() - started) * 1000
        return snapshot
