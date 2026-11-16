"""Proportional breakdowns with explicit denominators and missing-data reasons."""
from __future__ import annotations

from dataclasses import dataclass

from rich.cells import cell_len
from rich.console import Console, ConsoleOptions, RenderResult
from rich.measure import Measurement
from rich.text import Text

from .ram_bar import cell_widths
from .report import size
from .i18n import translate


@dataclass(frozen=True)
class MemoryPart:
    label: str
    short: str
    value: int
    color: str
    foreground: str = 'black'


@dataclass
class MemoryBreakdownBar:
    """One accounting dimension, never a sum of overlapping metrics."""

    metric: str
    total: int | None
    parts: tuple[MemoryPart, ...] = ()
    reason: str | None = None
    note: str | None = None
    language: str = 'it'

    @property
    def display_metric(self) -> str:
        return translate(self.language, 'uss_app') if self.metric == 'USS app' else self.metric

    @property
    def valid(self) -> bool:
        return (self.reason is None and self.total is not None and self.total >= 0
                and bool(self.parts) and all(p.value >= 0 for p in self.parts)
                and sum(p.value for p in self.parts) == self.total)

    def heading(self) -> Text:
        result = Text(f'{translate(self.language, "breakdown")} {self.display_metric} · '
                      f'{translate(self.language, "total").lower()} {size(self.total)}', style='bold')
        if not self.valid:
            result.append(' · n/a: ' + (self.reason or translate(self.language, 'invalid_parts')), style='yellow')
        elif self.note:
            result.append(' · ' + self.note, style='grey70')
        return result

    def render(self, width: int) -> Text:
        width = max(0, width)
        label = Text(self.display_metric + '  ')
        label.truncate(width, overflow='crop')
        result = Text(no_wrap=True, overflow='crop')
        result.append_text(label)
        remaining = width - label.cell_len
        if not self.valid:
            result.append('n/a'[:remaining], style='yellow')
            return result
        if self.total == 0:
            empty = Text('0 B · ' + translate(self.language, 'zero_memory'))
            empty.truncate(remaining, overflow='crop', pad=True)
            result.append(empty.plain, style='grey70 on #30363d')
            return result
        counts = cell_widths([p.value for p in self.parts], self.total, remaining)
        for part, count in zip(self.parts, counts):
            label_cells = cell_len(part.short)
            if count >= label_cells + 2:
                padding = count - label_cells
                caption = ' ' * (padding // 2) + part.short + ' ' * (padding - padding // 2)
            else:
                caption = ' ' * count
            result.append(caption, style=f'{part.foreground} on {part.color}')
        return result

    def legend(self) -> Text:
        result = Text()
        if not self.valid:
            return result
        for part in self.parts:
            if result:
                result.append('  ')
            result.append('■ ', style=part.color)
            result.append(f'{part.label} {size(part.value)}')
        return result

    def __rich_console__(self, console: Console, options: ConsoleOptions) -> RenderResult:
        yield self.render(options.max_width)

    def __rich_measure__(self, console: Console, options: ConsoleOptions) -> Measurement:
        return Measurement(min(cell_len(self.display_metric) + 2, options.max_width), options.max_width)
