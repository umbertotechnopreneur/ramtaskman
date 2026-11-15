"""Windows/macOS counters via psutil; no invented PSS or per-process swap."""
from __future__ import annotations

import ntpath

import psutil

from ..models import ProcessMemory, SystemMemory


class PsutilBackend:
    def __init__(self, platform: str) -> None:
        if platform not in ('windows', 'macos'):
            raise ValueError(platform)
        self.name = platform
        self.source = f'{platform}: psutil virtual_memory, swap_memory, memory_full_info'
        self.unsupported = {
            'pss': 'PSS non esposta da psutil su questo sistema',
            'swap': 'swap per processo non esposta; commit/pagefile non equivale a swap residente su disco',
            'swap_pss': 'SwapPSS non esposta da psutil su questo sistema',
        }

    def read_system(self) -> SystemMemory:
        m = psutil.virtual_memory()
        notes = []
        try:
            swap = psutil.swap_memory()
            swap_total, swap_used = swap.total, swap.used
        except (OSError, psutil.Error, NotImplementedError):
            swap_total = swap_used = None
            notes.append('Swap/pagefile globale non disponibile tramite psutil')
        if self.name == 'windows':
            notes.append('Swap globale: pagefile da psutil; non commit privato dei processi')
        else:
            notes.append('Disponibile da psutil: free + inactive; diversa da Memory Pressure di Activity Monitor')
        return SystemMemory(total=m.total, available=m.available, free=m.free,
                            cache=None, slab=None, swap_total=swap_total, swap_used=swap_used,
                            notes=notes)

    def read_identity(self, process: psutil.Process) -> ProcessMemory | None:
        started = process.create_time()
        name = process.name()
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
        try:
            executable = process.exe() or None
            if executable and self.name == 'windows':
                executable = ntpath.normcase(executable)
        except psutil.AccessDenied:
            executable = None
        row = ProcessMemory(process.pid, started, name, uid, executable, user=user)
        return row if process.is_running() else None

    def read_metrics(self, process: psutil.Process, row: ProcessMemory) -> ProcessMemory | None:
        try:
            basic = process.memory_info()
            row.rss = basic.rss
        except psutil.AccessDenied:
            row.reason = 'RSS: accesso negato'
        try:
            full = process.memory_full_info()
            row.rss = full.rss
            row.uss = getattr(full, 'uss', None)
            if row.uss is None:
                row.reason = 'USS non disponibile da psutil'
        except (psutil.AccessDenied, OSError, NotImplementedError):
            row.reason = 'USS: accesso negato o lettura non disponibile'
        # Do not use full.vms, full.private or full.pagefile as resident private RAM or swap.
        # PSS / Swap / SwapPSS intentionally stay None: backend capabilities explain why.
        return row if process.is_running() else None

    def read_process(self, process: psutil.Process) -> ProcessMemory | None:
        row = self.read_identity(process)
        return self.read_metrics(process, row) if row is not None else None
