"""Byte counts are integers; missing measurements are None, never zero."""
from __future__ import annotations

from dataclasses import dataclass, field
import ntpath
import posixpath


@dataclass
class ProcessMemory:
    pid: int
    started_at: float
    name: str
    uid: int | None
    executable: str | None
    rss: int | None = None
    pss: int | None = None
    uss: int | None = None
    swap: int | None = None
    swap_pss: int | None = None
    reason: str | None = None
    user: str | None = None
    app_id: str | None = None
    app_name: str | None = None
    app_source: str | None = None
    breakdown: dict[str, int | None] = field(default_factory=dict)

    @property
    def key(self) -> str:
        """Distinguish a reused PID from the process that previously owned it."""
        return f"pid:{self.pid}:{self.started_at}"


@dataclass
class ApplicationMemory:
    key: str
    name: str
    uid: int | None
    executable: str | None
    processes: list[ProcessMemory] = field(default_factory=list)
    user: str | None = None
    grouping: str = "executable"
    grouping_id: str | None = None
    membership_complete: bool = True

    def total(self, metric: str) -> int | None:
        """Return a total only when membership and every measurement are known."""
        values = [getattr(p, metric) for p in self.processes]
        # Do not disguise an incomplete group as a complete total.
        return sum(values) if self.membership_complete and values and all(v is not None for v in values) else None

    @property
    def measured(self) -> int:
        return sum(p.pss is not None for p in self.processes)


@dataclass
class WindowsSystemMemory:
    system_cache: int | None = None
    kernel_paged: int | None = None
    kernel_nonpaged: int | None = None
    commit_total: int | None = None
    commit_limit: int | None = None
    commit_peak: int | None = None
    reason: str | None = None


@dataclass
class LinuxSystemMemory:
    commit_total: int | None = None
    commit_limit: int | None = None


@dataclass
class SystemMemory:
    total: int
    available: int
    free: int
    cache: int | None
    slab: int | None
    swap_total: int | None
    swap_used: int | None
    cpu_percent: float | None = None
    pressure_percent: float | None = None
    notes: list[str] = field(default_factory=list)
    segments: dict[str, int] = field(default_factory=dict)
    segments_reason: str | None = None
    windows_details: WindowsSystemMemory | None = None
    linux_details: LinuxSystemMemory | None = None

    @property
    def used(self) -> int:
        return self.total - self.available


@dataclass
class Snapshot:
    taken: float
    system: SystemMemory
    processes: list[ProcessMemory]
    sample_ms: float = 0.0
    skipped: int = 0
    platform: str = "linux"
    source: str = "Linux procfs: meminfo, smaps_rollup; psutil RSS fallback"
    unsupported: dict[str, str] = field(default_factory=dict)
    # Optional bounded scans preserve enumeration status separately from row metrics.
    enumeration_complete: bool = True
    measurement_attempted: int | None = None
    measurement_deferred: int = 0

    @property
    def applications(self) -> list[ApplicationMemory]:
        """Group known members by explicit systemd instance or declared fallback."""
        groups: dict[tuple, ApplicationMemory] = {}
        for proc in self.processes:
            # Name-only grouping is explicitly marked as a heuristic in UI/docs.
            owner = proc.uid if proc.uid is not None else (proc.user or proc.key)
            explicit_app = (self.platform == 'linux' and proc.uid is not None
                            and proc.app_source == 'systemd-cgroup' and proc.app_id and proc.app_name)
            if explicit_app:
                grouping, grouping_id, app_name = 'cgroup', proc.app_id, proc.app_name
            else:
                grouping = 'executable' if proc.executable else 'name'
                grouping_id = proc.executable or proc.name
                # Backslashes are ordinary filename characters on Unix, but
                # path separators on Windows. Use the sampled OS, not the host.
                path_module = ntpath if self.platform == 'windows' else posixpath
                app_name = path_module.basename(proc.executable) if proc.executable else proc.name
            identity = (owner, grouping, grouping_id)
            if identity not in groups:
                groups[identity] = ApplicationMemory(
                    key=f"app:{identity!r}",
                    name=app_name,
                    uid=proc.uid, executable=proc.executable, user=proc.user,
                    grouping=grouping, grouping_id=grouping_id,
                    membership_complete=self.enumeration_complete,
                )
            group = groups[identity]
            group.processes.append(proc)
            # A cgroup can contain helpers with different executables: no single exe owns it.
            if group.executable != proc.executable:
                group.executable = None
        return list(groups.values())

    @property
    def measured(self) -> int:
        return sum(p.pss is not None for p in self.processes)

    def coverage(self, metric: str) -> int:
        return sum(getattr(p, metric) is not None for p in self.processes)

    def visible_sum(self, metric: str) -> int | None:
        values = [getattr(p, metric) for p in self.processes if getattr(p, metric) is not None]
        return sum(values) if values else None
