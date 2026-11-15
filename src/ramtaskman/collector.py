"""Platform-neutral sampling orchestration; UI sees only Snapshot."""
from __future__ import annotations

import sys
import time
from bisect import bisect_right
from collections.abc import Callable
from pathlib import Path

import psutil

from .models import Snapshot


def make_backend(platform: str | None = None, proc: Path = Path('/proc')):
    platform = platform or sys.platform
    if platform.startswith('linux'):
        from .backends.linux import LinuxBackend
        return LinuxBackend(proc)
    if platform in ('win32', 'darwin'):
        from .backends.psutil_backend import PsutilBackend
        return PsutilBackend('windows' if platform == 'win32' else 'macos')
    raise RuntimeError(f'Sistema non supportato: {platform}. Supportati: Linux, Windows, macOS.')


class Collector:
    def __init__(self, proc: Path = Path('/proc'), backend=None, *, max_measurements: int | None = None) -> None:
        if max_measurements is not None and (isinstance(max_measurements, bool) or
                                             not isinstance(max_measurements, int) or max_measurements < 1):
            raise ValueError('Il budget delle misure deve essere un intero positivo')
        self.backend = backend if backend is not None else make_backend(proc=proc)
        if max_measurements is not None and not (callable(getattr(self.backend, 'read_identity', None)) and
                                                 callable(getattr(self.backend, 'read_metrics', None))):
            raise ValueError('Il backend non supporta il campionamento a budget')
        self.max_measurements = max_measurements
        self._measurement_cursor: tuple[int, float] | None = None
        self._cpu_primed = False

    def sample(self, cancelled: Callable[[], bool] | None = None) -> Snapshot:
        start = time.monotonic()
        system = self.backend.read_system()
        cpu = psutil.cpu_percent(interval=None)
        system.cpu_percent = cpu if self._cpu_primed else None
        self._cpu_primed = True
        if self.max_measurements is not None:
            return self._sample_bounded(start, system, cancelled)
        rows = []
        skipped = 0
        complete = True
        for process in psutil.process_iter():
            if cancelled is not None and cancelled():
                complete = False
                break
            try:
                row = self.backend.read_process(process)
                if row is not None:
                    rows.append(row)
                else:
                    skipped += 1
            except (psutil.NoSuchProcess, psutil.ZombieProcess, FileNotFoundError, ProcessLookupError,
                    psutil.AccessDenied, PermissionError):
                skipped += 1
        return Snapshot(time.time(), system, rows, (time.monotonic() - start) * 1000, skipped,
                        platform=self.backend.name, source=self.backend.source,
                        unsupported=dict(self.backend.unsupported), enumeration_complete=complete and skipped == 0)

    def _sample_bounded(self, start, system, cancelled: Callable[[], bool] | None) -> Snapshot:
        """Enumerate all identities; rotate which processes receive fresh counters.

        No historical metrics are reused. If an identity cannot be read, group
        membership is globally incomplete, since the missing process may belong
        to any group. The optional budget limits expensive process measurements,
        not the OS enumeration or a syscall already in progress.
        """
        identities = []
        skipped = 0
        enumeration_complete = True
        for process in psutil.process_iter():
            if cancelled is not None and cancelled():
                enumeration_complete = False
                break
            try:
                row = self.backend.read_identity(process)
                if row is None:
                    skipped += 1
                else:
                    identities.append((process, row))
            except (psutil.NoSuchProcess, psutil.ZombieProcess, FileNotFoundError, ProcessLookupError,
                    psutil.AccessDenied, PermissionError):
                skipped += 1
        count = len(identities)
        scheduled = min(count, self.max_measurements)
        ordered_keys = sorted((row.pid, row.started_at) for _, row in identities)
        offset = (bisect_right(ordered_keys, self._measurement_cursor) % count
                  if count and self._measurement_cursor is not None else 0)
        selected_keys = [ordered_keys[(offset + i) % count] for i in range(scheduled)] if count else []
        chosen = set(selected_keys)
        rows = []
        attempted = 0
        interrupted = not enumeration_complete
        attempted_keys = set()
        for process, row in identities:
            if cancelled is not None and cancelled():
                interrupted = True
            if (row.pid, row.started_at) not in chosen or interrupted:
                row.reason = ('Misura rinviata: scansione annullata' if interrupted else
                              'Misura rinviata: budget di campionamento')
                rows.append(row)
                continue
            try:
                attempted += 1
                attempted_keys.add((row.pid, row.started_at))
                measured = self.backend.read_metrics(process, row)
                if measured is None:
                    skipped += 1
                else:
                    rows.append(measured)
            except (psutil.NoSuchProcess, psutil.ZombieProcess, FileNotFoundError, ProcessLookupError,
                    psutil.AccessDenied, PermissionError):
                skipped += 1
        # Advance only over the contiguous scheduled prefix actually attempted.
        for key in selected_keys:
            if key not in attempted_keys:
                break
            self._measurement_cursor = key
        return Snapshot(time.time(), system, rows, (time.monotonic() - start) * 1000, skipped,
                        platform=self.backend.name, source=self.backend.source,
                        unsupported=dict(self.backend.unsupported), enumeration_complete=enumeration_complete and skipped == 0,
                        measurement_attempted=attempted, measurement_deferred=count - attempted)
