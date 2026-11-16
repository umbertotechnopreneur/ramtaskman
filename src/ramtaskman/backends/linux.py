"""Linux procfs metadata only. No process memory, cmdlines or network access."""
from __future__ import annotations

from pathlib import Path

import psutil

from ..models import LinuxSystemMemory, ProcessMemory, SystemMemory
from ..memory_segments import partition_meminfo
from ..grouping import CGROUP_LIMIT, application_cgroup
from ..messages import message
from ..process_identity import process_executable, process_name


def parse_kib(text: str) -> dict[str, int]:
    """Only procfs kB fields are byte counts; ignore the smaps address header."""
    result = {}
    for line in text.splitlines():
        parts = line.split()
        if len(parts) == 3 and parts[0].endswith(':') and parts[2] == 'kB':
            result[parts[0][:-1]] = int(parts[1]) * 1024
    return result


def parse_rollup(text: str) -> dict[str, int | None]:
    fields = parse_kib(text)
    private = ('Private_Clean', 'Private_Dirty')
    return dict(
        rss=fields.get('Rss'), pss=fields.get('Pss'),
        uss=sum(fields[k] for k in private) if all(k in fields for k in private) else None,
        swap=fields.get('Swap'), swap_pss=fields.get('SwapPss'),
    )


BREAKDOWN_FIELDS = {
    'pss_anon': 'Pss_Anon', 'pss_file': 'Pss_File', 'pss_shmem': 'Pss_Shmem',
    'private_clean': 'Private_Clean', 'private_dirty': 'Private_Dirty',
    'shared_clean': 'Shared_Clean', 'shared_dirty': 'Shared_Dirty',
    'anonymous': 'Anonymous', 'lazy_free': 'LazyFree', 'anon_huge_pages': 'AnonHugePages',
}


def parse_breakdown(text: str) -> dict[str, int | None]:
    fields = parse_kib(text)
    return {key: fields.get(source) for key, source in BREAKDOWN_FIELDS.items()}


def read_app_cgroup(path: Path, uid: int | None) -> tuple[str, str] | None:
    if uid is None:
        return None
    try:
        with path.open('r', encoding='utf-8', errors='replace') as stream:
            text = stream.read(CGROUP_LIMIT + 1)
        return application_cgroup(text, uid)
    except OSError:
        return None


def read_pressure(path: Path) -> float | None:
    try:
        for line in path.read_text().splitlines():
            if line.startswith('some '):
                fields = dict(item.split('=', 1) for item in line.split()[1:])
                return float(fields['avg10'])
    except (OSError, KeyError, ValueError):
        pass
    return None


def read_system(proc: Path) -> SystemMemory:
    m = parse_kib((proc / 'meminfo').read_text())
    # Available overlaps reclaimable cache; never draw them as disjoint buckets.
    segments, segments_reason = partition_meminfo(m)
    cache_fields = ('Cached', 'Buffers', 'SReclaimable', 'Shmem')
    cache = (max(0, m['Cached'] + m['Buffers'] + m['SReclaimable'] - m['Shmem'])
             if all(field in m for field in cache_fields) else None)
    return SystemMemory(
        total=m['MemTotal'], available=m['MemAvailable'], free=m['MemFree'],
        cache=cache, slab=m.get('Slab'), swap_total=m['SwapTotal'],
        swap_used=m['SwapTotal'] - m['SwapFree'],
        pressure_percent=read_pressure(proc / 'pressure' / 'memory'),
        segments=segments, segments_reason=segments_reason,
        linux_details=LinuxSystemMemory(commit_total=m.get('Committed_AS'),
                                        commit_limit=m.get('CommitLimit')),
    )


class LinuxBackend:
    name = "linux"
    source = "Linux procfs: meminfo, smaps_rollup; psutil RSS fallback"
    unsupported: dict[str, str] = {}

    def __init__(self, proc: Path = Path('/proc')) -> None:
        self.proc = proc

    def read_system(self) -> SystemMemory:
        return read_system(self.proc)

    def read_identity(self, process: psutil.Process) -> ProcessMemory | None:
        pid = process.pid
        started = process.create_time()
        name = process_name(process)
        try:
            uid = process.uids().real
        except psutil.AccessDenied:
            uid = None
        executable = process_executable(process)
        row = ProcessMemory(pid, started, name, uid, executable)
        app = read_app_cgroup(self.proc / str(pid) / 'cgroup', uid)
        if app is not None:
            row.app_id, row.app_name = app
            row.app_source = 'systemd-cgroup'
        return row if process.is_running() else None

    def read_metrics(self, process: psutil.Process, row: ProcessMemory) -> ProcessMemory | None:
        pid = row.pid
        try:
            rollup = (self.proc / str(pid) / 'smaps_rollup').read_text()
            fields = parse_rollup(rollup)
            row.breakdown = parse_breakdown(rollup)
            for key, value in fields.items():
                setattr(row, key, value)
            if any(fields[k] is None for k in ('pss', 'uss', 'swap')):
                row.reason = message('tech_rollup_incomplete')
        except PermissionError:
            row.reason = message('tech_rollup_denied')
        except (FileNotFoundError, ProcessLookupError):
            row.reason = message('tech_rollup_absent')
        except OSError:
            row.reason = message('tech_rollup_unreadable')
        if row.rss is None:
            try:
                row.rss = process.memory_info().rss
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                pass
        # is_running checks the creation time, invalidating psutil's cached PID on reuse.
        return row if process.is_running() else None

    def read_process(self, process: psutil.Process) -> ProcessMemory | None:
        row = self.read_identity(process)
        return self.read_metrics(process, row) if row is not None else None
