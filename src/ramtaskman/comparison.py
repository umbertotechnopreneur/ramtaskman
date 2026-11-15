"""Conservative, OS-independent comparison of observed virtual intervals."""
from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Callable
from types import MappingProxyType
from typing import Mapping

from .capture_models import CaptureSnapshot, FrozenRegion, METRICS


class ComparisonCancelled(Exception):
    """The owner abandoned a comparison; no partial result is publishable."""


def _validate(regions: tuple[FrozenRegion, ...], cancelled: Callable[[], bool] | None = None) -> None:
    end = -1
    for index, r in enumerate(regions):
        if index % 256 == 0 and cancelled is not None and cancelled():
            raise ComparisonCancelled()
        if r.start < 0 or r.end <= r.start or r.start < end:
            raise ValueError('Regioni non ordinate, sovrapposte o non valide')
        end = r.end


def _backing(r: FrozenRegion) -> tuple | None:
    # File identity does not depend on pathname, which may change on rename/unlink.
    if r.inode:
        return ('file', r.device, r.inode, r.offset)
    # Anonymous VMA identity cannot be proven even if this signature is unchanged.
    if r.path and not r.path.startswith('['):
        return None  # A pathname alone cannot prove file identity.
    # Kernel special VMAs have identities distinct from ordinary anonymous
    # memory and from one another; mapping names inside the anonymous family
    # are metadata, never proof of allocation continuity.
    label = r.path
    if not label or label == '[heap]' or label == '[stack]' or label.startswith(('[stack:', '[anon:')):
        return ('anonymous',)
    return ('special', label)


def _sum(regions: tuple[FrozenRegion, ...], metric: str) -> int | None:
    values = [getattr(r, metric) for r in regions]
    return sum(values) if all(v is not None for v in values) else None


@dataclass(frozen=True)
class RegionComparison:
    before: tuple[FrozenRegion, ...]
    after: tuple[FrozenRegion, ...]
    status: str
    changes: tuple[str, ...]
    comparable_metrics: frozenset[str]

    @property
    def start(self) -> int:
        return min(r.start for r in self.before + self.after)

    @property
    def end(self) -> int:
        return max(r.end for r in self.before + self.after)

    @property
    def key(self) -> str:
        return f'{self.start:x}-{self.end:x}:{self.status}'

    def value_a(self, metric: str) -> int | None:
        return _sum(self.before, metric) if self.before else None

    def value_b(self, metric: str) -> int | None:
        return _sum(self.after, metric) if self.after else None

    def delta(self, metric: str) -> int | None:
        if metric not in self.comparable_metrics or self.status in ('backing_changed', 'backing_unverified', 'restructured', 'unobserved'):
            return None
        if self.status == 'only_a':
            a = self.value_a(metric)
            return -a if a is not None else None
        if self.status == 'only_b':
            b = self.value_b(metric)
            return b if b is not None else None
        a, b = self.value_a(metric), self.value_b(metric)
        return b - a if a is not None and b is not None else None


@dataclass(frozen=True)
class Comparison:
    before: CaptureSnapshot
    after: CaptureSnapshot
    compatible: bool
    reason: str | None
    reverse_order: bool
    rows: tuple[RegionComparison, ...]
    totals: Mapping[str, int | None]
    comparable_metrics: frozenset[str]


def _incompatibility(a: CaptureSnapshot, b: CaptureSnapshot) -> str | None:
    if not a.collection_session_id or a.collection_session_id != b.collection_session_id:
        return 'Origine/sessione non verificabile o differente'
    if (a.pid, a.started_at) != (b.pid, b.started_at):
        return 'Identità del processo differente'
    if (a.platform, a.backend_id, a.backend_version) != (b.platform, b.backend_id, b.backend_version):
        return 'Piattaforma o provider incompatibile'
    if not a.executable_identity or not b.executable_identity or a.executable_identity != b.executable_identity:
        return 'Immagine eseguibile cambiata o non verificabile'
    return None


def compare_captures(a: CaptureSnapshot, b: CaptureSnapshot,
                     cancelled: Callable[[], bool] | None = None) -> Comparison:
    """Compare A→B. Mappings are observations, not proof of allocation identity."""
    _validate(a.regions, cancelled)
    _validate(b.regions, cancelled)
    error = _incompatibility(a, b)
    metrics = frozenset(m for m in METRICS if a.metric_definitions.get(m) and
                        a.metric_definitions.get(m) == b.metric_definitions.get(m))
    reverse = b.sequence < a.sequence
    if error:
        return Comparison(a, b, False, error, reverse, (), MappingProxyType({m: None for m in METRICS}), metrics)
    rows = []
    # Interval overlap components in address order. Within each snapshot ranges are disjoint,
    # so transitive overlap can be collected in one merge pass without quadratic searches.
    events = sorted([(r.start, 0, r) for r in a.regions] + [(r.start, 1, r) for r in b.regions],
                    key=lambda item: (item[0], item[1]))
    pos = 0
    while pos < len(events):
        if pos % 256 == 0 and cancelled is not None and cancelled():
            raise ComparisonCancelled()
        _, side, first = events[pos]
        old = [first] if side == 0 else []
        new = [first] if side == 1 else []
        end = first.end
        pos += 1
        while pos < len(events) and events[pos][0] < end:
            if pos % 256 == 0 and cancelled is not None and cancelled():
                raise ComparisonCancelled()
            _, side, r = events[pos]
            (old if side == 0 else new).append(r)
            end = max(end, r.end)
            pos += 1
        old, new = tuple(old), tuple(new)
        changes = ()
        if not old:
            status = 'only_b' if a.complete else 'unobserved'
        elif not new:
            status = 'only_a' if b.complete else 'unobserved'
        elif len(old) != 1 or len(new) != 1 or (old[0].start, old[0].end) != (new[0].start, new[0].end):
            status = 'restructured'
        else:
            x, y = old[0], new[0]
            changes = tuple(k for k in ('permissions', 'path', 'category', 'device', 'inode', 'offset', 'vm_flags')
                            if getattr(x, k) != getattr(y, k))
            backing_a, backing_b = _backing(x), _backing(y)
            if backing_a is None or backing_b is None:
                status = 'backing_unverified'
            elif backing_a != backing_b:
                status = 'backing_changed'
            else:
                status = 'metadata_changed' if changes else 'same_interval'
        rows.append(RegionComparison(old, new, status, changes, metrics))
    totals = {}
    for m in METRICS:
        if cancelled is not None and cancelled():
            raise ComparisonCancelled()
        x, y = a.total(m), b.total(m)
        totals[m] = y - x if m in metrics and x is not None and y is not None else None
    return Comparison(a, b, True, None, reverse, tuple(rows), MappingProxyType(totals), metrics)
