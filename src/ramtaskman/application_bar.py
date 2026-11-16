"""USS consumption by complete application groups, never physical addresses."""
from __future__ import annotations

from .memory_bars import MemoryBreakdownBar, MemoryPart
from .models import ProcessMemory, Snapshot


COLORS = ('#3b82f6', '#22c55e', '#f59e0b', '#a78bfa', '#22d3ee',
          '#f472b6', '#f97316', '#a3e635', '#e879f9', '#2dd4bf')


def application_uss_bar(snapshot: Snapshot) -> MemoryBreakdownBar:
    apps = snapshot.applications
    complete = [(app, value) for app in apps
                if (value := app.total('uss')) is not None and value >= 0]
    complete.sort(key=lambda item: (-item[1], item[0].key))
    coverage = (f'Top 10 tra {len(complete)}/{len(apps)} app con USS completa · '
                f'processi USS {snapshot.coverage("uss")}/{len(snapshot.processes)}')
    if not complete:
        reason = ('identità incomplete' if not snapshot.enumeration_complete else 'nessuna app con USS completa')
        return MemoryBreakdownBar('USS app', None, reason=coverage + ' · ' + reason)
    parts = [MemoryPart(f'{index + 1}. {app.name} ({len(app.processes)} proc.)', str(index + 1), value,
                        COLORS[index], 'black')
             for index, (app, value) in enumerate(complete[:10])]
    if len(complete) > 10:
        parts.append(MemoryPart(f'Altre app complete ({len(complete) - 10})', 'Altre',
                                sum(value for _, value in complete[10:]), '#6b7280', 'white'))
    return MemoryBreakdownBar('USS app', sum(value for _, value in complete), tuple(parts), note=coverage)


def process_uss_bar(snapshot: Snapshot, process: ProcessMemory) -> MemoryBreakdownBar:
    current = next((p for p in snapshot.processes if p.key == process.key), None)
    if current is None or current.uss is None:
        return MemoryBreakdownBar('USS PID / RAM', None, reason='USS del processo non disponibile nel campione RAM')
    total, uss = snapshot.system.total, current.uss
    if total <= 0 or not 0 <= uss <= total:
        return MemoryBreakdownBar('USS PID / RAM', None, reason='contatori incoerenti')
    return MemoryBreakdownBar('USS PID / RAM', total, (
        MemoryPart(f'{current.name} · PID {current.pid} · USS', 'PID', uss, COLORS[0], 'white'),
        MemoryPart('Resto della RAM (inclusa disponibile)', 'Resto', total - uss, '#30363d', 'white'),
    ), note=f'USS {100 * uss / total:.2f}% della RAM totale; posizione convenzionale')
