"""On-demand Linux mapping metadata; never reads process memory or mapped files.

The normal collector deliberately keeps using smaps_rollup. A region scan is a
separate, bounded snapshot for one PID and create_time identity. Budgets and
cancellation are cooperative between procfs reads, not a hard syscall timeout.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
import re
import time

import psutil

from .models import ProcessMemory
from .messages import error_text, message
from .process_identity import process_executable


@dataclass
class MemoryRegion:
    start: int
    end: int
    permissions: str = '----'
    offset: int = 0
    device: str = '00:00'
    inode: int = 0
    path: str = ''
    category: str = 'anonymous'
    rss: int | None = None
    pss: int | None = None
    uss: int | None = None
    swap: int | None = None
    swap_pss: int | None = None
    breakdown: dict[str, int | None] = field(default_factory=dict)
    vm_flags: tuple[str, ...] = ()

    @property
    def size(self) -> int:
        return self.end - self.start

    @property
    def key(self) -> str:
        return f'{self.start:x}-{self.end:x}'


@dataclass
class RegionSnapshot:
    pid: int
    started_at: float
    name: str
    taken: float
    regions: list[MemoryRegion] = field(default_factory=list)
    sample_ms: float = 0.0
    reason: str | None = None
    complete: bool = True
    executable_identity: str | None = None

    def total(self, metric: str) -> int | None:
        """Only a complete scan and complete counters produce a process total."""
        if not self.complete:
            return None
        values = [getattr(region, metric) for region in self.regions]
        return sum(values) if all(value is not None for value in values) else None


_HEADER = re.compile(
    r'^([0-9a-fA-F]+)-([0-9a-fA-F]+)\s+([r-][w-][x-][ps])\s+'
    r'([0-9a-fA-F]+)\s+([0-9a-fA-F]+:[0-9a-fA-F]+)\s+(\d+)(?:\s+(.*))?$'
)
_HEADER_START = re.compile(r'^[0-9a-fA-F]+-[0-9a-fA-F]+\s')
_FIELDS = {
    'Size': 'size', 'Rss': 'rss', 'Pss': 'pss', 'Swap': 'swap', 'SwapPss': 'swap_pss',
    'Private_Clean': 'private_clean', 'Private_Dirty': 'private_dirty',
    'Shared_Clean': 'shared_clean', 'Shared_Dirty': 'shared_dirty',
    'Anonymous': 'anonymous', 'LazyFree': 'lazy_free', 'AnonHugePages': 'anon_huge_pages',
    'ShmemPmdMapped': 'shmem_pmd_mapped', 'FilePmdMapped': 'file_pmd_mapped',
    'Shared_Hugetlb': 'shared_hugetlb', 'Private_Hugetlb': 'private_hugetlb',
    'Referenced': 'referenced', 'Locked': 'locked',
    'KernelPageSize': 'kernel_page_size', 'MMUPageSize': 'mmu_page_size',
}
_BREAKDOWN = tuple(value for value in _FIELDS.values()
                   if value not in ('size', 'rss', 'pss', 'swap', 'swap_pss'))


def classify_region(path: str, executable: str | None = None) -> str:
    """Mapping origin/name heuristic, not the type of every resident page.

    In particular, a file-backed VMA can contain anonymous CoW pages. Unnamed
    anonymous regions are not assumed to be heaps or thread stacks.
    """
    normalized = path.removesuffix(' (deleted)')
    if normalized == '[heap]':
        return 'heap'
    if normalized == '[stack]' or normalized.startswith('[stack:'):
        return 'stack'
    if normalized.startswith(('[anon_shmem:', '/dev/shm/', '/SYSV', '/memfd:', 'memfd:')):
        return 'shmem'
    if not normalized or normalized.startswith('[anon:'):
        return 'anonymous'
    if normalized.startswith('['):
        return 'special'
    if executable and normalized == executable.removesuffix(' (deleted)'):
        return 'executable'
    filename = PurePosixPath(normalized).name
    if filename.endswith('.so') or '.so.' in filename:
        return 'library'
    return 'file'


class _SmapsParser:
    def __init__(self, executable: str | None = None) -> None:
        self.executable = executable
        self.current: MemoryRegion | None = None
        self.values: dict[str, int] = {}
        self.previous_end = 0

    def finish(self) -> MemoryRegion | None:
        region = self.current
        if region is None:
            return None
        if 'size' in self.values and self.values['size'] != region.size:
            raise ValueError(message('tech_smaps_size_mismatch'))
        for key in ('rss', 'pss', 'swap', 'swap_pss'):
            setattr(region, key, self.values.get(key))
        region.breakdown = {key: self.values.get(key) for key in _BREAKDOWN}
        if all(key in self.values for key in ('private_clean', 'private_dirty')):
            region.uss = self.values['private_clean'] + self.values['private_dirty']
        self.current = None
        self.values = {}
        return region

    def feed(self, line: str) -> MemoryRegion | None:
        line = line.rstrip('\r\n')
        if not line:
            return None
        match = _HEADER.fullmatch(line)
        if match:
            start, end = int(match[1], 16), int(match[2], 16)
            if start >= end or start < self.previous_end:
                raise ValueError(message('tech_smaps_overlap'))
            done = self.finish()
            path = match[7] or ''
            self.current = MemoryRegion(
                start, end, match[3], int(match[4], 16), match[5], int(match[6]),
                path, classify_region(path, self.executable),
            )
            self.previous_end = end
            return done
        if self.current is None or _HEADER_START.match(line):
            raise ValueError(message('tech_smaps_header'))
        source, separator, payload = line.partition(':')
        if source == 'VmFlags' and separator:
            self.current.vm_flags = tuple(payload.split())
        elif source in _FIELDS:
            fields = payload.split()
            if not separator or len(fields) != 2 or not fields[0].isdigit() or fields[1] != 'kB':
                raise ValueError(message('tech_smaps_counter_invalid', counter=source))
            key = _FIELDS[source]
            if key in self.values:
                raise ValueError(message('tech_smaps_counter_duplicate', counter=source))
            self.values[key] = int(fields[0]) * 1024
        # Other kernel/version-specific counters are deliberately ignored.
        return None


def parse_smaps(text: str, executable: str | None = None) -> list[MemoryRegion]:
    """Parse a complete smaps document. Missing counters remain None."""
    parser = _SmapsParser(executable)
    regions = []
    for line in text.splitlines():
        region = parser.feed(line)
        if region is not None:
            regions.append(region)
    last = parser.finish()
    if last is not None:
        regions.append(last)
    return regions


class LinuxRegionReader:
    def __init__(self, proc_root: Path = Path('/proc'), *, max_bytes: int = 32 << 20,
                 max_regions: int = 32768, max_seconds: float = 3.0) -> None:
        if max_bytes <= 0 or max_regions <= 0 or max_seconds <= 0:
            raise ValueError(message('tech_scan_limits_positive'))
        self.proc_root = Path(proc_root)
        self.max_bytes = max_bytes
        self.max_regions = max_regions
        self.max_seconds = max_seconds

    @staticmethod
    def _verify_identity(process: ProcessMemory) -> str | None:
        # A fresh Process avoids psutil's cached create_time across the read.
        current = psutil.Process(process.pid)
        if current.create_time() != process.started_at or not current.is_running():
            raise ProcessLookupError(message('tech_process_gone'))
        return process_executable(current)

    def read(self, process: ProcessMemory,
             cancelled: Callable[[], bool] | None = None) -> RegionSnapshot:
        started = time.monotonic()
        snap = RegionSnapshot(process.pid, process.started_at, process.name, time.time())
        parser = _SmapsParser(process.executable)
        consumed = 0

        def stop_reason() -> str | None:
            if cancelled is not None and cancelled():
                return message('tech_cancelled')
            if time.monotonic() - started >= self.max_seconds:
                return message('tech_time_limit')
            return None

        try:
            snap.reason = stop_reason()
            if snap.reason:
                snap.complete = False
                return snap
            before_exe = self._verify_identity(process)
            if before_exe and process.executable and before_exe != process.executable:
                raise ProcessLookupError(message('tech_executable_changed'))
            with (self.proc_root / str(process.pid) / 'smaps').open('rb') as stream:
                while True:
                    snap.reason = stop_reason()
                    if snap.reason:
                        snap.complete = False
                        break
                    # One extra byte distinguishes exact-budget EOF from truncation;
                    # an excessive path/line is also bounded independently.
                    line = stream.readline(min(self.max_bytes - consumed + 1, 65537))
                    consumed += len(line)
                    if consumed > self.max_bytes or len(line) > 65536:
                        snap.reason = message('tech_read_limit')
                        snap.complete = False
                        break
                    if not line:
                        last = parser.finish()
                        if last is not None:
                            snap.regions.append(last)
                        break
                    region = parser.feed(line.decode('utf-8', errors='replace'))
                    if region is not None:
                        snap.regions.append(region)
                        if len(snap.regions) >= self.max_regions:
                            snap.reason = message('tech_region_limit')
                            snap.complete = False
                            break
            after_exe = self._verify_identity(process)
            if before_exe and after_exe and before_exe != after_exe:
                raise ProcessLookupError(message('tech_executable_changed'))
            snap.executable_identity = before_exe if before_exe and before_exe == after_exe else None
            # A slow final read/identity check must not claim completion after
            # cancellation or a time-budget overrun.
            reason = stop_reason()
            if reason:
                snap.reason, snap.complete = reason, False
        except (PermissionError, psutil.AccessDenied):
            snap.reason = message('tech_smaps_denied')
            snap.complete = False
            snap.regions.clear()
        except (ProcessLookupError, FileNotFoundError, psutil.NoSuchProcess):
            snap.reason = message('tech_process_smaps_missing')
            snap.complete = False
            snap.regions.clear()
        except (OSError, ValueError) as error:
            snap.reason = message('tech_smaps_error', type=type(error).__name__, reason=error_text(error))
            snap.complete = False
            snap.regions.clear()
        finally:
            snap.sample_ms = (time.monotonic() - started) * 1000
        return snap
