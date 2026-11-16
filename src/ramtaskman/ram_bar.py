"""Full-width OS accounting bar, distinct from a map of physical addresses."""
from __future__ import annotations

from rich.console import Console, ConsoleOptions, RenderResult
from rich.measure import Measurement
from rich.text import Text
from rich.cells import cell_len

from .models import SystemMemory
from .i18n import translate
from .report import size
from .messages import message

# key, legend, in-bar label, color, contrasting text
SEGMENTS = (
    ('anon', 'Anonima', 'Anon', '#3b82f6', 'white'),
    ('file_cache', 'File cache', 'File', '#22c55e', 'black'),
    ('shmem', 'Condivisa/tmpfs', 'Shm', '#a78bfa', 'black'),
    ('buffers', 'Buffer', 'Buffer', '#22d3ee', 'black'),
    ('slab_reclaimable', 'Slab ric.', 'Slab R', '#eab308', 'black'),
    ('slab_unreclaimable', 'Slab non ric.', 'Slab NR', '#f97316', 'black'),
    ('other', 'Altro (residuo)', 'Altro', '#6b7280', 'white'),
    ('free', 'Libera', 'Libera', '#30363d', 'white'),
)
FALLBACK = (
    ('used', 'In uso', 'In uso', '#3b82f6', 'white'),
    ('available', 'Disponibile', 'Disponibile', '#30363d', 'white'),
)
_LABEL_KEYS = {
    'anon': 'anonymous', 'file_cache': 'file_cache_label', 'shmem': 'shared', 'buffers': 'buffers',
    'slab_reclaimable': 'slab_reclaimable_label', 'slab_unreclaimable': 'slab_unreclaimable_label',
    'other': 'other', 'free': 'free', 'used': 'in_use', 'available': 'available',
}


def cell_widths(values: list[int], total: int, width: int) -> list[int]:
    """Largest remainders: all columns accounted for, no data renormalization."""
    if total <= 0 or any(value < 0 for value in values) or sum(values) != total:
        raise ValueError(message('ram_partition_error'))
    width = max(0, width)
    cells = [value * width // total for value in values]
    order = sorted(range(len(values)), key=lambda i: -(values[i] * width % total))
    for index in order[:width - sum(cells)]:
        cells[index] += 1
    return cells


class SystemRamBar:
    """Rich renderable uses the actual panel width, including after resize."""
    def __init__(self, memory: SystemMemory, language: str = 'it') -> None:
        self.memory = memory
        self.language = language

    @property
    def detailed(self) -> bool:
        return bool(self.memory.segments)

    def parts(self):
        if self.detailed:
            return [(spec, self.memory.segments[spec[0]]) for spec in SEGMENTS]
        return [(FALLBACK[0], self.memory.used), (FALLBACK[1], self.memory.available)]

    def render(self, width: int) -> Text:
        label = 'RAM  '[:max(0, width)]
        result = Text(label, no_wrap=True, overflow='crop')
        parts = self.parts()
        try:
            cells = cell_widths([value for _, value in parts], self.memory.total, max(0, width - len(label)))
        except ValueError:
            # Invalid system totals must never resemble a valid partition.
            result.append('n/a', style='yellow')
            return result
        for (spec, _), count in zip(parts, cells):
            key, _, short, color, foreground = spec
            short = translate(self.language, _LABEL_KEYS[key])
            label_cells = cell_len(short)
            if count >= label_cells + 2:
                padding = count - label_cells
                caption = ' ' * (padding // 2) + short + ' ' * (padding - padding // 2)
            else:
                caption = ' ' * count
            result.append(caption, style=f'{foreground} on {color}')
        return result

    def legend(self) -> Text:
        result = Text()
        for spec, value in self.parts():
            key, label, _, color, _ = spec
            label = translate(self.language, _LABEL_KEYS[key])
            if result:
                result.append('  ')
            result.append('■ ', style=color)
            result.append(f'{label} {size(value)}')
        return result

    def __rich_console__(self, console: Console, options: ConsoleOptions) -> RenderResult:
        yield self.render(options.max_width)

    def __rich_measure__(self, console: Console, options: ConsoleOptions) -> Measurement:
        return Measurement(min(6, options.max_width), options.max_width)
