"""Windows/macOS counters via psutil; no invented PSS or per-process swap."""
from __future__ import annotations

import ntpath

import psutil

from ..models import ProcessMemory, SystemMemory
from ..messages import message
from ..process_identity import process_executable, process_name


class PsutilBackend:
    def __init__(self, platform: str) -> None:
        if platform not in ('windows', 'macos'):
            raise ValueError(platform)
        self.name = platform
        self.source = f'{platform}: psutil virtual_memory, swap_memory, memory_full_info'
        if platform == 'windows':
            self.source += '; Windows GetPerformanceInfo'
        self.unsupported = {
            'pss': message('tech_pss_unsupported'),
            'swap': message('tech_swap_unsupported'),
            'swap_pss': message('tech_swappss_unsupported'),
        }

    def read_system(self) -> SystemMemory:
        m = psutil.virtual_memory()
        details = None
        notes = []
        try:
            swap = psutil.swap_memory()
            swap_total, swap_used = swap.total, swap.used
        except (OSError, psutil.Error, NotImplementedError):
            swap_total = swap_used = None
            notes.append(message('tech_global_swap_unavailable'))
        if self.name == 'windows':
            from .windows_system import read_windows_system
            details = read_windows_system()
            notes.append(message('tech_global_swap_windows'))
        else:
            notes.append(message('tech_available_macos'))
        return SystemMemory(total=m.total, available=m.available, free=m.free,
                            cache=None, slab=None, swap_total=swap_total, swap_used=swap_used,
                            notes=notes, windows_details=details)

    def read_identity(self, process: psutil.Process) -> ProcessMemory | None:
        started = process.create_time()
        name = process_name(process)
        uid = None
        user = None
        if self.name == 'macos':
            try:
                uid = process.uids().real
            except psutil.AccessDenied:
                pass
        else:
            try:
                user = process.username()
            except psutil.AccessDenied:
                pass
        executable = process_executable(process)
        if executable and self.name == 'windows':
            executable = ntpath.normcase(executable)
        row = ProcessMemory(process.pid, started, name, uid, executable, user=user)
        return row if process.is_running() else None

    def read_metrics(self, process: psutil.Process, row: ProcessMemory) -> ProcessMemory | None:
        try:
            basic = process.memory_info()
            row.rss = basic.rss
        except psutil.AccessDenied:
            row.reason = message('tech_rss_denied')
        try:
            full = process.memory_full_info()
            row.rss = full.rss
            row.uss = getattr(full, 'uss', None)
            # A successful full read also recovers RSS after a denied basic read.
            row.reason = message('tech_uss_missing') if row.uss is None else None
        except (psutil.AccessDenied, OSError, NotImplementedError):
            uss_reason = message('tech_uss_denied')
            row.reason = message('tech_reasons_join', first=row.reason, second=uss_reason) if row.reason else uss_reason
        # Do not use full.vms, full.private or full.pagefile as resident private RAM or swap.
        # PSS / Swap / SwapPSS intentionally stay None: backend capabilities explain why.
        return row if process.is_running() else None

    def read_process(self, process: psutil.Process) -> ProcessMemory | None:
        row = self.read_identity(process)
        return self.read_metrics(process, row) if row is not None else None
