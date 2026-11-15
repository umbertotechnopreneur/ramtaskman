"""Platform-neutral sampling orchestration; UI sees only Snapshot."""
from __future__ import annotations

import sys
import time
import threading
import math
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
    def __init__(self, proc: Path = Path('/proc'), backend=None, *, max_measurements: int | None = None,
                 selected_priority: bool = False, measurement_backoff: bool = False,
                 slow_seconds: float = .25) -> None:
        if max_measurements is not None and (isinstance(max_measurements, bool) or
                                             not isinstance(max_measurements, int) or max_measurements < 1):
            raise ValueError('Il budget delle misure deve essere un intero positivo')
        self.backend = backend if backend is not None else make_backend(proc=proc)
        if max_measurements is not None and not (callable(getattr(self.backend, 'read_identity', None)) and
                                                 callable(getattr(self.backend, 'read_metrics', None))):
            raise ValueError('Il backend non supporta il campionamento a budget')
        self.max_measurements = max_measurements
        if (selected_priority or measurement_backoff) and max_measurements is None:
            raise ValueError('Priorità e backoff richiedono un budget di misure')
        if not math.isfinite(slow_seconds) or slow_seconds <= 0:
            raise ValueError('La soglia lenta deve essere positiva')
        self.selected_priority = selected_priority
        self.measurement_backoff = measurement_backoff
        self.slow_seconds = slow_seconds
        self._priority_lock = threading.Lock()
        self._priority_key: tuple[int, float] | None = None
        self._cycle = 0
        # key -> (consecutive costly/denied attempts, next retry cycle, reason)
        self._backoff: dict[tuple[int, float], tuple[int, int, str]] = {}
        self._measurement_cursor: tuple[int, float] | None = None
        self._cpu_primed = False

    def set_priority(self, key: tuple[int, float] | None) -> None:
        """Safely set one selected PID+start; disabling priority keeps default behaviour."""
        with self._priority_lock:
            self._priority_key = key

    def _record_cost(self, key: tuple[int, float], elapsed: float, denied: bool) -> None:
        if not self.measurement_backoff:
            return
        if not denied and elapsed < self.slow_seconds:
            self._backoff.pop(key, None)
            return
        streak = self._backoff.get(key, (0, 0, ''))[0] + 1
        delay = 0 if streak < 2 else min(8, 2 ** min(streak - 2, 3))
        self._backoff[key] = (streak, self._cycle + delay + 1,
                              'accesso negato' if denied else 'lettura lenta')

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
        self._cycle += 1
        ordered_keys = sorted((row.pid, row.started_at) for _, row in identities)
        if enumeration_complete and skipped == 0:
            alive = set(ordered_keys)
            self._backoff = {key: value for key, value in self._backoff.items() if key in alive}
        else:
            # A long sequence of incomplete enumerations must not retain an
            # unbounded history of disappeared PIDs. Dropping a record merely
            # permits a fresh attempt; it never fabricates a measurement.
            self._backoff = {key: value for key, value in self._backoff.items()
                             if self._cycle - value[1] <= 128}
        eligible_keys = [key for key in ordered_keys if not self.measurement_backoff or
                         self._backoff.get(key, (0, 0, ''))[1] <= self._cycle]
        scheduled = min(len(eligible_keys), self.max_measurements)
        offset = (bisect_right(ordered_keys, self._measurement_cursor) % count
                  if count and self._measurement_cursor is not None else 0)
        # One reserved slot at most; with budget 1 only every third cycle, so
        # normal round-robin still makes progress even for a pinned PID.
        with self._priority_lock:
            priority = self._priority_key
        use_priority = (self.selected_priority and priority in eligible_keys and scheduled > 0 and
                        (self.max_measurements > 1 or self._cycle % 3 == 1) and len(eligible_keys) > 1)
        selected_keys = [priority] if use_priority else []
        selected_set = set(selected_keys)
        eligible = set(eligible_keys)
        for i in range(count):
            key = ordered_keys[(offset + i) % count]
            if len(selected_keys) >= scheduled:
                break
            if key in eligible and key not in selected_set:
                selected_keys.append(key)
                selected_set.add(key)
        rotation_keys = [key for key in selected_keys if not (use_priority and key == priority)]
        chosen = selected_set
        rows = []
        attempted = 0
        interrupted = not enumeration_complete
        attempted_keys = set()
        for process, row in identities:
            if cancelled is not None and cancelled():
                interrupted = True
            if (row.pid, row.started_at) not in chosen or interrupted:
                backoff = self._backoff.get((row.pid, row.started_at)) if self.measurement_backoff else None
                row.reason = ('Misura rinviata: scansione annullata' if interrupted else
                              f'Misura rinviata: backoff ({backoff[2]})' if backoff and backoff[1] > self._cycle else
                              'Misura rinviata: budget di campionamento')
                rows.append(row)
                continue
            key = (row.pid, row.started_at)
            measurement_start = time.monotonic()
            try:
                attempted += 1
                attempted_keys.add(key)
                measured = self.backend.read_metrics(process, row)
                if measured is None:
                    skipped += 1
                else:
                    denied = bool(measured.reason and 'accesso negato' in measured.reason.casefold())
                    self._record_cost(key, time.monotonic() - measurement_start, denied)
                    rows.append(measured)
            except (psutil.AccessDenied, PermissionError):
                self._record_cost(key, time.monotonic() - measurement_start, True)
                row.rss = row.pss = row.uss = row.swap = row.swap_pss = None
                row.breakdown = {}
                row.reason = 'Misura: accesso negato'
                rows.append(row)
            except (psutil.NoSuchProcess, psutil.ZombieProcess, FileNotFoundError, ProcessLookupError):
                skipped += 1
        # Advance only over the contiguous scheduled prefix actually attempted.
        for key in rotation_keys:
            if key not in attempted_keys:
                break
            self._measurement_cursor = key
        return Snapshot(time.time(), system, rows, (time.monotonic() - start) * 1000, skipped,
                        platform=self.backend.name, source=self.backend.source,
                        unsupported=dict(self.backend.unsupported), enumeration_complete=enumeration_complete and skipped == 0,
                        measurement_attempted=attempted, measurement_deferred=count - attempted)
