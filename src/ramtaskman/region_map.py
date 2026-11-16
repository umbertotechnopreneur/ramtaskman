"""Address-ordered terminal map of region metadata, never physical frames."""
from __future__ import annotations

from bisect import bisect_right
from itertools import groupby

from rich.cells import cell_len
from rich.text import Text
from textual import events
from textual.message import Message
from textual.widgets import Static

from .regions import MemoryRegion
from .i18n import translate

CATEGORIES = {
    'executable': ('Eseguibile', '#60a5fa'),
    'library': ('Libreria (euristica)', '#4ade80'),
    'file': ('File', '#22d3ee'),
    'heap': ('Heap riconosciuto', '#fb923c'),
    'stack': ('Stack riconosciuto', '#eab308'),
    'anonymous': ('Anonima', '#a78bfa'),
    'shmem': ('Shmem', '#f472b6'),
    'special': ('Speciale', '#6b7280'),
}


def region_cells(regions: list[MemoryRegion], mode: str, width: int) -> list[str | None]:
    """Sample proportional columns; tiny regions remain accessible in the table.

    Virtual holes have no area. A separator marks a visible transition across a
    hole (or hidden region); it is deliberately not a representation of its size.
    Missing RSS prevents drawing a misleading complete resident map.
    """
    ordered = sorted(regions, key=lambda r: r.start)
    values = [r.size if mode == 'virtual' else r.rss for r in ordered]
    if width <= 0 or any(v is None or v < 0 for v in values):
        return []
    positive = [(r, v) for r, v in zip(ordered, values) if v > 0]
    total = sum(v for _, v in positive)
    if not total:
        return []
    ends, current = [], 0
    for _, value in positive:
        current += value
        ends.append(current)
    indices = [bisect_right(ends, (2 * x + 1) * total // (2 * width)) for x in range(width)]
    cells = [positive[i][0].key for i in indices]
    if mode == 'virtual':
        for x in range(1, width):
            left, right = positive[indices[x-1]][0], positive[indices[x]][0]
            if left.key != right.key and left.end < right.start:
                cells[x] = None
    return cells


class RegionMap(Static):
    DEFAULT_CSS = 'RegionMap { height: 1; }'

    class Chosen(Message):
        def __init__(self, key: str) -> None:
            super().__init__()
            self.key = key

    def __init__(self, *, language: str = 'it', **kwargs):
        super().__init__(**kwargs)
        self.language = language
        self.regions: list[MemoryRegion] = []
        self.mode = 'resident'
        self.selected: str | None = None

    def set_regions(self, regions: list[MemoryRegion], mode: str, selected: str | None) -> None:
        self.regions, self.mode, self.selected = regions, mode, selected
        self.refresh()

    def render(self) -> Text:
        if self.content_size.width <= 0:
            return Text('')
        if not self.regions:
            return Text(translate(self.language, 'no_regions'), style='grey70')
        if self.mode == 'resident' and any(r.rss is None or r.rss < 0 for r in self.regions):
            return Text(translate(self.language, 'rss_unavailable'), style='yellow')
        cells = region_cells(self.regions, self.mode, self.content_size.width)
        if not cells:
            return Text(translate(self.language, 'zero_rss'), style='grey70')
        lookup = {r.key: r for r in self.regions}
        result = Text(no_wrap=True, overflow='crop')
        for key, run in groupby(cells):
            width = sum(1 for _ in run)
            if key is None:
                result.append('│' * width, style='grey70')
                continue
            category = lookup[key].category if lookup[key].category in CATEGORIES else 'special'
            _, color = CATEGORIES[category]
            label = translate(self.language, 'category_' + category)
            label = label.split(' (', 1)[0]
            caption = ('◆ ' if key == self.selected else '') + label
            if cell_len(caption) > width:
                caption = '◆' if key == self.selected else ''
            padding = width - cell_len(caption)
            result.append(' ' * (padding // 2) + caption + ' ' * (padding - padding // 2),
                          style=f'black on {color}')
        return result

    def on_click(self, event: events.Click) -> None:
        cells = region_cells(self.regions, self.mode, self.content_size.width)
        if 0 <= event.x < len(cells) and cells[event.x] is not None:
            self.post_message(self.Chosen(cells[event.x]))
        event.stop()

    def on_resize(self) -> None:
        self.refresh()
