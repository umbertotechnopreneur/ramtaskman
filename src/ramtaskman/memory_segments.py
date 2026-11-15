"""A disjoint accounting view of Linux meminfo, not physical address ranges.

Cached includes shmem/tmpfs, so only Cached - Shmem is the file-cache segment.
MemAvailable, Slab (the parent of SReclaimable/SUnreclaim), Mapped and PSS are
not additional parts. ``other`` is a derived residual, not measured kernel RAM.
Sources: https://docs.kernel.org/filesystems/proc.html#meminfo
https://github.com/torvalds/linux/blob/master/fs/proc/meminfo.c
"""
from __future__ import annotations


_REQUIRED = ('MemTotal', 'MemFree', 'AnonPages', 'Cached', 'Shmem', 'Buffers',
             'SReclaimable', 'SUnreclaim')


def partition_meminfo(fields: dict[str, int]) -> tuple[dict[str, int], str | None]:
    """Return byte segments or a reason why this sample cannot be partitioned.

    Kernel counters are sampled sequentially. Never hide inconsistent samples by
    clipping a negative value or scaling parts to fit the total. Positive residual
    bytes remain explicitly unclassified; several kernel allocations are not in
    this selected set of counters. MemTotal is usable RAM, not installed DIMM size.
    """
    missing = [name for name in _REQUIRED if name not in fields]
    if missing:
        return {}, 'Ripartizione RAM non disponibile: campi meminfo assenti (' + ', '.join(missing) + ')'
    if any(fields[name] < 0 for name in _REQUIRED) or fields['MemTotal'] == 0:
        return {}, 'Ripartizione RAM non disponibile: contatori meminfo negativi o totale nullo'
    if fields['Cached'] < fields['Shmem']:
        return {}, 'Ripartizione RAM non disponibile: campione incoerente (Cached < Shmem)'
    segments = dict(
        anon=fields['AnonPages'],
        file_cache=fields['Cached'] - fields['Shmem'],
        shmem=fields['Shmem'],
        buffers=fields['Buffers'],
        slab_reclaimable=fields['SReclaimable'],
        slab_unreclaimable=fields['SUnreclaim'],
    )
    known = sum(segments.values()) + fields['MemFree']
    if known > fields['MemTotal']:
        return {}, 'Ripartizione RAM non disponibile: somma dei contatori superiore a MemTotal'
    segments['other'] = fields['MemTotal'] - known
    segments['free'] = fields['MemFree']
    return segments, None
