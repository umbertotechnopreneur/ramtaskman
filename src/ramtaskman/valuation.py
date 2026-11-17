"""Hardware-value allocation, never a bill, RSS sum or price feed."""
from dataclasses import dataclass
import math
import re

from .models import ApplicationMemory, ProcessMemory, Snapshot


@dataclass(frozen=True)
class RamPrice:
    amount: float
    currency: str = 'EUR'
    months: int | None = None
    capacity_gib: float | None = None

    def __post_init__(self):
        if not math.isfinite(self.amount) or self.amount <= 0:
            raise ValueError('RAM price must be finite and positive')
        if not re.fullmatch(r'[A-Z]{3}', self.currency):
            raise ValueError('Currency must be a three-letter uppercase code')
        if self.months is not None and (type(self.months) is not int or self.months < 1):
            raise ValueError('Allocation months must be a positive integer')
        if self.capacity_gib is not None and (not math.isfinite(self.capacity_gib) or not 0 < self.capacity_gib <= 2**30):
            raise ValueError('RAM capacity must be finite, positive and at most 2^30 GiB')


def value_row(row: ApplicationMemory | ProcessMemory, snap: Snapshot, price: RamPrice) -> dict:
    # One basis per platform: never silently replace a failed PSS read by USS/RSS.
    metric = 'pss' if snap.platform == 'linux' else 'uss'
    processes = row.processes if isinstance(row, ApplicationMemory) else [row]
    complete = not isinstance(row, ApplicationMemory) or row.membership_complete
    values = [getattr(p, metric) for p in processes]
    unique = len({p.key for p in processes}) == len(processes)
    amount = sum(values) if complete and unique and values and all(v is not None and v >= 0 for v in values) else None
    capacity = int(price.capacity_gib * (1 << 30)) if price.capacity_gib is not None else snap.system.total
    reason = None
    if not complete or not unique or amount is None:
        reason = 'incomplete_measurement_or_membership'
    elif capacity <= 0 or amount > capacity:
        reason = 'invalid_capacity_or_inconsistent_measurement'
    value = price.amount * (amount / capacity) if reason is None else None
    return dict(basis=metric.upper(), shared_memory='proportional' if metric == 'pss' else 'excluded',
                bytes=amount, capacity_bytes=capacity, capacity_source='configured' if price.capacity_gib is not None else 'os_visible',
                hardware_value=value, monthly_value=value / price.months if value is not None and price.months else None,
                currency=price.currency, months=price.months, reason=reason)


def value_text(row, snap, price):
    result = value_row(row, snap, price)
    value = result['monthly_value'] if price.months else result['hardware_value']
    return 'n/a' if value is None else f'{value:.2f} {price.currency}'


def price_report(snap, price):
    return dict(price=price.amount, currency=price.currency, months=price.months,
                note='Hardware value allocation, not a charge or guaranteed saving. PSS apportions shared pages; USS excludes them. Groups and processes overlap: do not add both. Sequential samples are not atomic.',
                applications=[dict(key=row.key, name=row.name, **value_row(row,snap,price)) for row in snap.applications],
                processes=[dict(key=row.key, **value_row(row,snap,price)) for row in snap.processes])
