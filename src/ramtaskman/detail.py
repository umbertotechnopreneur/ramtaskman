"""Granular procfs counters: overlapping views, never an invented RAM partition."""
from rich.console import Group
from rich.table import Table
from rich.text import Text

from .models import ApplicationMemory, ProcessMemory
from .memory_bars import MemoryBreakdownBar, MemoryPart
from .report import size
from .i18n import translate

BREAKDOWN = (
    ('pss_anon', 'PSS anonima', 'detail_desc_pss_anon'),
    ('pss_file', 'PSS file', 'detail_desc_pss_file'),
    ('pss_shmem', 'PSS shmem', 'detail_desc_pss_shmem'),
    ('private_clean', 'Privata clean', 'detail_desc_private_clean'),
    ('private_dirty', 'Privata dirty', 'detail_desc_private_dirty'),
    ('shared_clean', 'Condivisa clean', 'detail_desc_shared_clean'),
    ('shared_dirty', 'Condivisa dirty', 'detail_desc_shared_dirty'),
    ('anonymous', 'Anonymous', 'detail_desc_anonymous'),
    ('lazy_free', 'LazyFree', 'detail_desc_lazy_free'),
    ('anon_huge_pages', 'AnonHugePages', 'detail_desc_anon_huge_pages'),
)

PSS_PARTS = (
    ('pss_anon', 'Anonima', 'Anon', '#3b82f6', 'white'),
    ('pss_file', 'File', 'File', '#22c55e', 'black'),
    ('pss_shmem', 'Shmem', 'Shmem', '#a78bfa', 'black'),
)
RSS_PARTS = (
    ('private_clean', 'Privata clean', 'Priv C', '#60a5fa', 'black'),
    ('private_dirty', 'Privata dirty', 'Priv D', '#3b82f6', 'white'),
    ('shared_clean', 'Condivisa clean', 'Cond C', '#86efac', 'black'),
    ('shared_dirty', 'Condivisa dirty', 'Cond D', '#22c55e', 'black'),
)


_PART_LABELS = {
    'pss_anon': 'detail_anon', 'pss_file': 'detail_file', 'pss_shmem': 'detail_shmem',
    'private_clean': 'detail_private_clean', 'private_dirty': 'detail_private_dirty',
    'shared_clean': 'detail_shared_clean', 'shared_dirty': 'detail_shared_dirty',
}
_SHORT_LABELS = {
    'private_clean': 'detail_short_private_clean',
    'private_dirty': 'detail_short_private_dirty',
    'shared_clean': 'detail_short_shared_clean',
    'shared_dirty': 'detail_short_shared_dirty',
}


def detail_bars(row: ApplicationMemory | ProcessMemory, language: str = 'it') -> tuple[MemoryBreakdownBar, ...]:
    """Check each member before summing: opposing inconsistencies must not cancel."""
    def tr(key: str, **values: object) -> str:
        return translate(language, key, **values)

    processes = row.processes if isinstance(row, ApplicationMemory) else [row]
    membership_complete = not isinstance(row, ApplicationMemory) or row.membership_complete
    bars = []
    for metric, specs in (('pss', PSS_PARTS), ('rss', RSS_PARTS)):
        total = row.total(metric) if isinstance(row, ApplicationMemory) else getattr(row, metric)
        complete = [proc for proc in processes if getattr(proc, metric) is not None
                    and all(proc.breakdown.get(spec[0]) is not None for spec in specs)]
        if not processes or len(complete) != len(processes) or not membership_complete:
            reason = tr('detail_components_missing', complete=len(complete), total=len(processes))
            bars.append(MemoryBreakdownBar(metric.upper(), total, reason=reason, language=language))
            continue

        # Validate the accounting of every member before adding the group.
        residual = 0
        inconsistent = False
        for proc in complete:
            values = [proc.breakdown[spec[0]] for spec in specs]
            measured = getattr(proc, metric)
            difference = measured - sum(values)
            # Linux prints each fixed-point PSS counter in whole KiB independently.
            # floor(a+b+c) - floor(a)-floor(b)-floor(c) is 0, 1 or 2 KiB.
            # Keep that residual visible; never scale components to hide a mismatch.
            # Source: Linux fs/proc/task_mmu.c, __show_smap(), v6.17.
            rounding = (metric == 'pss' and 0 <= difference <= 2 * 1024
                        and all(value % 1024 == 0 for value in [measured, *values]))
            if measured < 0 or any(value < 0 for value in values) or (difference != 0 and not rounding):
                inconsistent = True
                break
            residual += difference
        if inconsistent:
            bars.append(MemoryBreakdownBar(metric.upper(), total, reason=
                tr('detail_components_inconsistent'), language=language))
            continue

        parts = []
        for key, _, short, color, foreground in specs:
            label = tr(_PART_LABELS[key])
            short_label = tr(_SHORT_LABELS[key]) if key in _SHORT_LABELS else label
            value = sum(proc.breakdown[key] for proc in complete)
            parts.append(MemoryPart(label, short_label, value, color, foreground))

        note = None
        if residual:
            parts.append(MemoryPart(tr('detail_rounding_label'), tr('detail_rounding_short'),
                                    residual, '#6b7280', 'white'))
            note = tr('detail_rounding_note', size=size(residual))
        bars.append(MemoryBreakdownBar(metric.upper(), total, tuple(parts), note=note, language=language))
    return tuple(bars)


def breakdown_total(row: ApplicationMemory | ProcessMemory, metric: str) -> tuple[int | None, int, int]:
    processes = row.processes if isinstance(row, ApplicationMemory) else [row]
    values = [proc.breakdown.get(metric) for proc in processes]
    count = sum(value is not None for value in values)
    membership_complete = not isinstance(row, ApplicationMemory) or row.membership_complete
    value = sum(values) if membership_complete and values and count == len(values) else None
    return value, count, len(values)


def breakdown_summary(row: ApplicationMemory | ProcessMemory, language: str = 'it') -> Text:
    """Summarize the three PSS components without changing the selected sample."""
    parts = []
    for key in ('pss_anon', 'pss_file', 'pss_shmem'):
        label = translate(language, _PART_LABELS[key]).lower()
        value, _, _ = breakdown_total(row, key)
        parts.append(f'{label} {size(value)}')
    hint = translate(language, 'detail_summary_hint')
    return Text('PSS: ' + ' · '.join(parts) + ' · ' + hint, style='cyan')


def detail_content(row: ApplicationMemory | ProcessMemory, platform: str, language: str = 'it') -> Group:
    """Render one fixed sample; unrelated memory views must not be added together."""
    def tr(key: str, **values: object) -> str:
        return translate(language, key, **values)

    processes = row.processes if isinstance(row, ApplicationMemory) else [row]
    title = Text(tr('detail_title') + ' · ' + row.name, style='bold')
    source = Text(tr('detail_source'), style='grey70')
    if platform != 'linux':
        source = Text(tr('detail_unsupported', platform=platform), style='yellow')
    table = Table(expand=True)
    for label in (tr('detail_counter'), tr('detail_memory'), tr('readings'), tr('detail_meaning')):
        table.add_column(label)
    for key, label, description_key in BREAKDOWN:
        value, count, total = breakdown_total(row, key)
        translated_label = tr(_PART_LABELS[key]) if key in _PART_LABELS else label
        if key in ('pss_anon', 'pss_file', 'pss_shmem'):
            translated_label = 'PSS ' + translated_label
        table.add_row(translated_label, size(value), f'{count}/{total}', tr(description_key))
    notes = Text(tr('detail_notes'), style='yellow')
    metrics = []
    for key in ('pss', 'uss', 'rss', 'swap', 'swap_pss'):
        value = row.total(key) if isinstance(row, ApplicationMemory) else getattr(row, key)
        metrics.append(f'{key.upper()} {size(value)}')
    summary = Text(' · '.join(metrics), style='bold')
    identity = Text()
    if isinstance(row, ApplicationMemory):
        identity.append(tr('group_' + row.grouping) + '\n')
        identity.append(row.grouping_id or tr('detail_identity_missing'))
        identity.append('\n' + tr('detail_group_count', count=len(processes)))
    else:
        identity.append(f'PID {row.pid} · {tr("executable")} {row.executable or "n/a"}')
    bars = []
    for bar in detail_bars(row, language):
        bars.extend((bar.heading(), bar, bar.legend()))
    swap = Text(f'{tr("detail_swap_resident")} {size(row.total("swap") if isinstance(row, ApplicationMemory) else row.swap)}'
                f' · SwapPSS {size(row.total("swap_pss") if isinstance(row, ApplicationMemory) else row.swap_pss)}',
                style='cyan')
    return Group(title, summary, source, identity, *bars, swap, table, notes,
                 Text(tr('detail_fixed'), style='grey70'))
