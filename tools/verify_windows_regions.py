"""Prova nativa Windows di regioni e pagine del SOLO processo di test.

Allocazione controllata, nessun accesso a memoria altrui e nessun salvataggio
automatico. Il conteggio dei bit Valid è un'osservazione sperimentale, non RSS.
"""
from __future__ import annotations

import argparse
import ctypes
import json
import os
import platform
import struct
import sys
import time
from typing import Protocol

MEM_COMMIT = 0x1000
MEM_RESERVE = 0x2000
MEM_RELEASE = 0x8000
MEM_FREE = 0x10000
PAGE_READWRITE = 0x04
PROBE_BYTES = 8 * 1024 * 1024
BATCH_PAGES = 256
_STATES = {MEM_COMMIT: 'MEM_COMMIT', MEM_RESERVE: 'MEM_RESERVE', MEM_FREE: 'MEM_FREE'}


class QueryError(RuntimeError):
    pass


class ProbeAPI(Protocol):
    def page_size(self) -> int: ...
    def reserve(self, size: int) -> int: ...
    def commit(self, address: int, size: int) -> None: ...
    def touch(self, address: int, size: int, page_size: int) -> None: ...
    def query_region(self, address: int) -> dict: ...
    def query_pages(self, addresses: list[int]) -> list[int]: ...
    def release(self, address: int) -> None: ...


class _PageInfo(ctypes.Structure):
    _fields_ = [('virtual_address', ctypes.c_void_p), ('flags', ctypes.c_size_t)]


class NativeAPI:
    def __init__(self) -> None:
        if sys.platform != 'win32' or ctypes.sizeof(ctypes.c_void_p) != 8:
            raise RuntimeError('Questa verifica richiede Python Windows a 64 bit.')
        # Lazy imports keep --help and unit tests usable on other platforms.
        from ramtaskman.backends.windows_regions import _NativeAPI
        self.virtual_query = _NativeAPI()
        self.dll = self.virtual_query.dll
        self.dll.GetCurrentProcess.argtypes = []
        self.dll.GetCurrentProcess.restype = ctypes.c_void_p
        self.process = self.dll.GetCurrentProcess()  # pseudo-handle; do not close
        self.dll.VirtualAlloc.argtypes = [ctypes.c_void_p, ctypes.c_size_t,
                                          ctypes.c_uint32, ctypes.c_uint32]
        self.dll.VirtualAlloc.restype = ctypes.c_void_p
        self.dll.VirtualFree.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_uint32]
        self.dll.VirtualFree.restype = ctypes.c_int
        self.dll.K32QueryWorkingSetEx.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint32]
        self.dll.K32QueryWorkingSetEx.restype = ctypes.c_int

    def page_size(self) -> int:
        return self.virtual_query.limits()[2]

    def reserve(self, size: int) -> int:
        ptr = self.dll.VirtualAlloc(None, size, MEM_RESERVE, PAGE_READWRITE)
        if not ptr:
            raise ctypes.WinError(ctypes.get_last_error())
        return int(ptr)

    def commit(self, address: int, size: int) -> None:
        ptr = self.dll.VirtualAlloc(ctypes.c_void_p(address), size, MEM_COMMIT, PAGE_READWRITE)
        if not ptr:
            raise ctypes.WinError(ctypes.get_last_error())
        if int(ptr) != address:
            raise RuntimeError('VirtualAlloc ha restituito un indirizzo inatteso')

    def touch(self, address: int, size: int, page_size: int) -> None:
        # Write only to the test's own freshly committed allocation, one byte per page.
        for offset in range(0, size, page_size):
            ctypes.memset(ctypes.c_void_p(address + offset), 1, 1)

    def query_region(self, address: int) -> dict:
        region = self.virtual_query.query(self.process, address)
        return {'start': hex(region.start), 'size_bytes': region.size,
                'state': _STATES.get(region.state, f'0x{region.state:x}'),
                'protection': f'0x{region.protection:x}', 'type': f'0x{region.type:x}'}

    def query_pages(self, addresses: list[int]) -> list[int]:
        data = (_PageInfo * len(addresses))(*(_PageInfo(addr, 0) for addr in addresses))
        ok = self.dll.K32QueryWorkingSetEx(self.process, data, ctypes.sizeof(data))
        if not ok:
            raise ctypes.WinError(ctypes.get_last_error())
        return [int(row.flags) for row in data]

    def release(self, address: int) -> None:
        if not self.dll.VirtualFree(ctypes.c_void_p(address), 0, MEM_RELEASE):
            raise ctypes.WinError(ctypes.get_last_error())

    def check_provider(self, address: int) -> dict:
        import psutil
        from ramtaskman.backends.windows_regions import WindowsRegionProvider
        from ramtaskman.models import ProcessMemory
        proc = psutil.Process()
        selected = ProcessMemory(proc.pid, proc.create_time(), 'probe-windows', None, proc.exe())
        snap = WindowsRegionProvider().read(selected)
        found = next((r for r in snap.regions if r.start <= address < r.end), None)
        return {'complete': snap.complete, 'reason': snap.reason,
                'region_found': bool(found), 'rss': found.rss if found else None,
                'source': 'WindowsRegionProvider; il contatore RSS per regione resta non disponibile'}


def sample_pages(api: ProbeAPI, address: int, size: int, page_size: int) -> dict:
    """Count queried bits; a batch error makes the full count unknown, never zero."""
    addresses = range(address, address + size, page_size)
    requested = len(addresses)
    seen = valid = invalid = 0
    try:
        for start in range(0, requested, BATCH_PAGES):
            batch = list(addresses[start:start + BATCH_PAGES])
            flags = api.query_pages(batch)
            if len(flags) != len(batch):
                raise QueryError('QueryWorkingSetEx ha restituito un batch incompleto')
            seen += len(flags)
            valid += sum(bool(value & 1) for value in flags)
            invalid += sum(not bool(value & 1) for value in flags)
    except (OSError, RuntimeError, ValueError) as error:
        return {'pages_requested': requested, 'pages_queried': seen,
                'valid_bit_1': None, 'valid_bit_0': None,
                'complete': False, 'reason': str(error)}
    return {'pages_requested': requested, 'pages_queried': seen,
            'valid_bit_1': valid, 'valid_bit_0': invalid, 'complete': True, 'reason': None}


def run_probe(api: ProbeAPI, *, size: int = PROBE_BYTES, hold_seconds: float = 0) -> dict:
    page_size = api.page_size()
    if page_size <= 0 or size <= 0 or size > PROBE_BYTES or size % page_size:
        raise ValueError('Dimensione prova o pagina non valida')
    if not 0 <= hold_seconds <= 300:
        raise ValueError('Attesa compresa fra 0 e 300 secondi')
    result = {'page_size_bytes': page_size, 'allocation_bytes': size, 'stages': {}}
    address = api.reserve(size)
    try:
        if not address or address % page_size:
            raise ValueError('Indirizzo riservato non valido')
        result['stages']['reserved'] = {'region': api.query_region(address),
                                        'pages': sample_pages(api, address, size, page_size)}
        api.commit(address, size)
        result['stages']['committed'] = {'region': api.query_region(address),
                                         'pages': sample_pages(api, address, size, page_size)}
        api.touch(address, size, page_size)
        result['stages']['touched'] = {'region': api.query_region(address),
                                       'pages': sample_pages(api, address, size, page_size)}
        if hasattr(api, 'check_provider'):
            result['provider'] = api.check_provider(address)
        if hold_seconds:
            print(f'PID {os.getpid()}: allocazione di prova disponibile per {hold_seconds:g} s.',
                  file=sys.stderr, flush=True)
            time.sleep(hold_seconds)
    finally:
        api.release(address)
    result['stages']['released'] = {'region': api.query_region(address),
                                    'pages': sample_pages(api, address, size, page_size)}
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description='Prova Windows di regioni/pagine sul proprio processo.')
    parser.add_argument('--hold-seconds', type=float, default=0,
                        help='secondi di attesa dopo il touch, per osservare il processo nella UI (0–300)')
    args = parser.parse_args()
    if not 0 <= args.hold_seconds <= 300:
        parser.error('--hold-seconds deve essere compreso fra 0 e 300')
    try:
        api = NativeAPI()
        report = run_probe(api, hold_seconds=args.hold_seconds)
    except (RuntimeError, OSError, ValueError) as error:
        print(f'Verifica non disponibile: {error}', file=sys.stderr)
        return 1
    report['environment'] = {'system': platform.system(), 'release': platform.release(),
                             'version': platform.version(), 'machine': platform.machine(),
                             'python': platform.python_version(), 'python_bits': struct.calcsize('P') * 8}
    report['interpretation'] = ('Valid=1/0 sono bit riportati da QueryWorkingSetEx; '
                                'non sono una misura equivalente di RSS o USS.')
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
