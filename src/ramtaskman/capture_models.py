"""Immutable on-demand captures, with explicit origin and metric semantics."""
from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Mapping
from uuid import uuid4

from .regions import MemoryRegion, RegionSnapshot

METRICS = ('rss', 'pss', 'uss', 'swap', 'swap_pss', 'size')
LINUX_METRIC_DEFINITIONS = {
    'rss': 'linux.smaps.Rss.bytes', 'pss': 'linux.smaps.Pss.bytes',
    'uss': 'linux.smaps.Private_Clean+Private_Dirty.bytes',
    'swap': 'linux.smaps.Swap.bytes', 'swap_pss': 'linux.smaps.SwapPss.bytes',
    'size': 'virtual.interval.bytes',
}


@dataclass(frozen=True)
class FrozenRegion:
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
    breakdown: Mapping[str, int | None] = field(default_factory=dict)
    vm_flags: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        # Frozen dataclasses alone do not freeze nested dict/list inputs.
        object.__setattr__(self, 'breakdown', MappingProxyType(dict(self.breakdown)))
        object.__setattr__(self, 'vm_flags', tuple(self.vm_flags))

    @property
    def size(self) -> int:
        return self.end - self.start

    @property
    def key(self) -> str:
        return f'{self.start:x}-{self.end:x}'


def freeze_region(region: MemoryRegion | FrozenRegion) -> FrozenRegion:
    return FrozenRegion(start=region.start, end=region.end, permissions=region.permissions,
                        offset=region.offset, device=region.device, inode=region.inode,
                        path=region.path, category=region.category, rss=region.rss, pss=region.pss,
                        uss=region.uss, swap=region.swap, swap_pss=region.swap_pss,
                        breakdown=region.breakdown, vm_flags=region.vm_flags)


@dataclass(frozen=True)
class CaptureSnapshot:
    pid: int
    started_at: float
    name: str
    taken: float
    regions: tuple[FrozenRegion, ...]
    sample_ms: float
    reason: str | None
    complete: bool
    capture_id: str
    collection_session_id: str
    sequence: int
    platform: str
    backend_id: str
    executable_identity: str | None = None
    metric_definitions: Mapping[str, str] = field(default_factory=dict)
    backend_version: str = '1'
    capabilities: Mapping[str, bool] = field(default_factory=dict)
    metric_coverage: Mapping[str, tuple[int, int]] = field(default_factory=dict)
    issues: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, 'regions', tuple(freeze_region(r) for r in self.regions))
        object.__setattr__(self, 'metric_definitions', MappingProxyType(dict(self.metric_definitions)))
        object.__setattr__(self, 'capabilities', MappingProxyType(dict(self.capabilities)))
        object.__setattr__(self, 'metric_coverage', MappingProxyType({k: tuple(v) for k, v in self.metric_coverage.items()}))
        object.__setattr__(self, 'issues', tuple(self.issues))

    @property
    def enumeration_complete(self) -> bool:
        return self.complete

    def total(self, metric: str) -> int | None:
        if not self.complete or metric not in METRICS:
            return None
        values = [getattr(r, metric) for r in self.regions]
        return sum(values) if all(value is not None for value in values) else None


def freeze_snapshot(snapshot: RegionSnapshot | CaptureSnapshot, *, collection_session_id: str,
                    sequence: int, platform: str = 'linux', backend_id: str = 'linux-smaps',
                    executable_identity: str | None = None,
                    metric_definitions: Mapping[str, str] | None = None,
                    capture_id: str | None = None, backend_version: str = '1',
                    capabilities: Mapping[str, bool] | None = None) -> CaptureSnapshot:
    """Create an independent, recursively frozen copy of a region snapshot."""
    definitions = dict(LINUX_METRIC_DEFINITIONS if metric_definitions is None and platform == 'linux'
                       else (metric_definitions or {}))
    regions = tuple(freeze_region(r) for r in snapshot.regions)
    coverage = {m: (sum(getattr(r, m) is not None for r in regions), len(regions)) for m in METRICS}
    return CaptureSnapshot(pid=snapshot.pid, started_at=snapshot.started_at, name=snapshot.name,
        taken=snapshot.taken, sample_ms=snapshot.sample_ms, reason=snapshot.reason,
        complete=snapshot.complete, regions=regions, capture_id=capture_id or str(uuid4()),
        collection_session_id=collection_session_id, sequence=sequence, platform=platform,
        backend_id=backend_id, backend_version=backend_version, executable_identity=executable_identity,
        metric_definitions=definitions, capabilities=capabilities or {m: m in definitions for m in METRICS},
        metric_coverage=coverage, issues=(snapshot.reason,) if snapshot.reason else ())
