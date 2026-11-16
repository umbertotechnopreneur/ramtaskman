"""Human and JSON output share the same measured snapshot and null rules."""
from dataclasses import asdict

from rich.table import Table
from rich.text import Text

from .models import Snapshot
from .i18n import translate

METRICS = ('pss', 'uss', 'rss', 'swap', 'swap_pss')


def size(value: int | None) -> str:
    if value is None:
        return 'n/a'
    for divisor, suffix in ((1 << 30, 'GiB'), (1 << 20, 'MiB'), (1 << 10, 'KiB')):
        if value >= divisor:
            return f'{value / divisor:.2f} {suffix}'
    return f'{value} B'


def to_dict(snap: Snapshot) -> dict:
    result = asdict(snap)
    result.update(
        schema_version=1,
        source=snap.source,
        grouping='Linux systemd user app instance when available; else User + executable/name (heuristic); unknown owner kept separate',
        measured_processes=snap.measured,
        coverage={metric: snap.coverage(metric) for metric in METRICS},
        visible_pss_bytes=snap.visible_sum('pss'),
        visible_pss_is_partial=(snap.measured != len(snap.processes) or snap.skipped > 0
                                or not snap.enumeration_complete),
        notes=[
            'System used = total - available; availability semantics depend on OS; cache may overlap available memory.',
            'Process RSS can double-count shared pages. PSS distributes them proportionally.',
            'Linux process Swap excludes shmem swap; SwapPss apportions shared swap. On Windows/macOS both are unavailable.',
            'Missing or incomplete totals are null. Samples are sequential, not atomic.',
        ],
        applications=[dict(
            key=app.key, name=app.name, uid=app.uid, user=app.user, executable=app.executable,
            grouping=app.grouping, grouping_id=app.grouping_id,
            membership_complete=app.membership_complete,
            pids=[p.pid for p in app.processes], measured=app.measured,
            **{key: app.total(key) for key in METRICS},
        ) for app in snap.applications],
    )
    result['system']['used'] = snap.system.used
    return result


def table(snap: Snapshot, language: str = 'it') -> Table:
    """Display labels are localized; sort fields and JSON identifiers are stable."""
    def tr(key: str) -> str:
        return translate(language, key)

    title = f'ramtaskman · {snap.platform} · {tr("applications").lower()}'
    result = Table(title=title, highlight=False)
    for label in (tr('report_application'), tr('processes'), 'PSS', 'USS', 'RSS', 'Swap',
                  tr('readings'), tr('report_group')):
        result.add_column(label)
    sort_metric = 'uss' if 'pss' in snap.unsupported else 'pss'
    for app in sorted(snap.applications, key=lambda a: (a.total(sort_metric) is None, -(a.total(sort_metric) or 0))):
        result.add_row(Text(app.name), str(len(app.processes)),
                       *(size(app.total(m)) for m in ('pss', 'uss', 'rss', 'swap')),
                       f'P {app.measured}/{len(app.processes)} U {sum(p.uss is not None for p in app.processes)}/{len(app.processes)}',
                       Text(tr('group_' + app.grouping)))
    return result
