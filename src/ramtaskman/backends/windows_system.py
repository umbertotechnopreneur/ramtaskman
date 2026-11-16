"""Documented, read-only Windows system counters; values overlap physical RAM.

https://learn.microsoft.com/windows/win32/api/psapi/ns-psapi-performance_information
"""
from __future__ import annotations

import ctypes
import sys

from ..models import WindowsSystemMemory


class PerformanceInformation(ctypes.Structure):
    _fields_ = [('cb', ctypes.c_uint32)] + [
        (name, ctypes.c_size_t) for name in (
            'CommitTotal', 'CommitLimit', 'CommitPeak', 'PhysicalTotal',
            'PhysicalAvailable', 'SystemCache', 'KernelTotal', 'KernelPaged',
            'KernelNonpaged', 'PageSize')
    ] + [(name, ctypes.c_uint32) for name in ('HandleCount', 'ProcessCount', 'ThreadCount')]


def read_windows_system() -> WindowsSystemMemory:
    if sys.platform != 'win32':
        return WindowsSystemMemory(reason='GetPerformanceInfo disponibile solo su Windows')
    try:
        api = ctypes.WinDLL('kernel32', use_last_error=True).K32GetPerformanceInfo
        api.argtypes = [ctypes.POINTER(PerformanceInformation), ctypes.c_uint32]
        api.restype = ctypes.c_int
        info = PerformanceInformation()
        info.cb = ctypes.sizeof(info)
        if not api(ctypes.byref(info), info.cb):
            raise ctypes.WinError(ctypes.get_last_error())
        return decode_performance_info(info)
    except (OSError, AttributeError, ValueError) as exc:
        return WindowsSystemMemory(reason=f'GetPerformanceInfo non disponibile: {exc}')


def decode_performance_info(info: PerformanceInformation) -> WindowsSystemMemory:
    if info.PageSize <= 0:
        raise ValueError('dimensione pagina non valida')
    return WindowsSystemMemory(**{
        field: int(getattr(info, native)) * int(info.PageSize)
        for field, native in (
            ('system_cache', 'SystemCache'), ('kernel_paged', 'KernelPaged'),
            ('kernel_nonpaged', 'KernelNonpaged'), ('commit_total', 'CommitTotal'),
            ('commit_limit', 'CommitLimit'), ('commit_peak', 'CommitPeak'))
    })
