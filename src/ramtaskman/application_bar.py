"""USS consumption by complete application groups, never physical addresses."""
from __future__ import annotations

from .memory_bars import MemoryBreakdownBar, MemoryPart
from .models import ProcessMemory, Snapshot
from .i18n import translate


COLORS = ('#3b82f6', '#22c55e', '#f59e0b', '#a78bfa', '#22d3ee',
          '#f472b6', '#f97316', '#a3e635', '#e879f9', '#2dd4bf')


def application_uss_bar(snapshot: Snapshot, language: str = 'it') -> MemoryBreakdownBar:
    apps = snapshot.applications
    complete = [(app, value) for app in apps
                if (value := app.total('uss')) is not None and value >= 0]
    complete.sort(key=lambda item: (-item[1], item[0].key))
    coverage = translate(language, 'uss_coverage', complete=len(complete), total=len(apps),
                         measured=snapshot.coverage('uss'), processes=len(snapshot.processes))
    if not complete:
        reason = translate(language, 'uss_identity_incomplete' if not snapshot.enumeration_complete else 'uss_no_apps')
        return MemoryBreakdownBar('USS app', None, reason=coverage + ' · ' + reason, language=language)
    process_label = translate(language, 'processes').lower()
    parts = [MemoryPart(f'{index + 1}. {app.name} ({len(app.processes)} {process_label})', str(index + 1), value,
                        COLORS[index], 'black')
             for index, (app, value) in enumerate(complete[:10])]
    if len(complete) > 10:
        parts.append(MemoryPart(translate(language, 'uss_others', count=len(complete) - 10), '+',
                                sum(value for _, value in complete[10:]), '#6b7280', 'white'))
    return MemoryBreakdownBar('USS app', sum(value for _, value in complete), tuple(parts), note=coverage, language=language)


def process_uss_bar(snapshot: Snapshot, process: ProcessMemory, language: str = 'it') -> MemoryBreakdownBar:
    current = next((p for p in snapshot.processes if p.key == process.key), None)
    if current is None or current.uss is None:
        return MemoryBreakdownBar('USS PID / RAM', None, reason=translate(language, 'uss_pid_unavailable'), language=language)
    total, uss = snapshot.system.total, current.uss
    if total <= 0 or not 0 <= uss <= total:
        return MemoryBreakdownBar('USS PID / RAM', None, reason=translate(language, 'inconsistent'), language=language)
    return MemoryBreakdownBar('USS PID / RAM', total, (
        MemoryPart(f'{current.name} · PID {current.pid} · USS', 'PID', uss, COLORS[0], 'white'),
        MemoryPart(translate(language, 'uss_rest'), 'RAM', total - uss, '#30363d', 'white'),
    ), note=translate(language, 'uss_pid_note', percent=f'{100 * uss / total:.2f}'), language=language)
