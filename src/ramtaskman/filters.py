"""Display filters never remove members from an application's accounting."""
from __future__ import annotations

from dataclasses import dataclass

from .models import ApplicationMemory, ProcessMemory

MEMORY_FILTERS = (('Tutta la memoria', 'all'), ('Con swap', 'swap'), ('Dati parziali', 'partial'))


def owner_key(proc: ProcessMemory | ApplicationMemory) -> str | None:
    if proc.uid is not None:
        return f'uid:{proc.uid}'
    if proc.user:
        return f'user:{proc.user}'
    return None


def owner_options(processes: list[ProcessMemory]) -> list[tuple[str, str]]:
    users = {}
    for proc in processes:
        key = owner_key(proc)
        if key is not None:
            users[key] = str(proc.uid) if proc.uid is not None else proc.user
    return [('Tutti gli utenti', 'all'), *sorted(((label, key) for key, label in users.items()),
                                              key=lambda item: item[0].casefold())]


@dataclass(frozen=True)
class RowFilter:
    query: str = ''
    owner: str = 'all'
    memory: str = 'all'

    @property
    def active(self) -> bool:
        return bool(self.query.strip() or self.owner != 'all' or self.memory != 'all')

    def matches(self, row: ProcessMemory | ApplicationMemory, unsupported: dict[str, str]) -> bool:
        processes = row.processes if isinstance(row, ApplicationMemory) else [row]
        if self.owner != 'all' and owner_key(row) != self.owner:
            return False
        query = self.query.strip().casefold()
        if query:
            # Exact PID lookup if the query consists of digits; otherwise literal substring.
            if query.isdecimal():
                if not any(str(proc.pid) == query for proc in processes):
                    return False
            else:
                names = [row.name, row.executable or '']
                for proc in processes:
                    names.extend((proc.name, proc.executable or '', proc.app_name or ''))
                if not any(query in name.casefold() for name in names):
                    return False
        if self.memory == 'swap':
            # Group matches if any member has measured swap, even when the total is partial.
            return any(proc.swap is not None and proc.swap > 0 for proc in processes)
        if self.memory == 'partial':
            supported = [metric for metric in ('pss', 'uss', 'rss', 'swap', 'swap_pss')
                         if metric not in unsupported]
            return any(getattr(proc, metric) is None for proc in processes for metric in supported)
        return True
