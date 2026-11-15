"""Proportional breakdowns with explicit denominators and missing-data reasons."""
from __future__ import annotations

from dataclasses import dataclass

from rich.console import Console, ConsoleOptions, RenderResult
from rich.measure import Measurement
from rich.text import Text

from .ram_bar import cell_widths
from .report import size


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

    @property
    def valid(self) -> bool:
        return (self.reason is None and self.total is not None and self.total >= 0
                and bool(self.parts) and all(p.value >= 0 for p in self.parts)
                and sum(p.value for p in self.parts) == self.total)

    def heading(self) -> Text:
        result = Text(f'Ripartizione {self.metric} · totale {size(self.total)}', style='bold')
        if not self.valid:
            result.append(' · n/a: ' + (self.reason or 'componenti incoerenti con il totale'), style='yellow')
        elif self.note:
            result.append(' · ' + self.note, style='grey70')
        return result

    def render(self, width: int) -> Text:
        width = max(0, width)
        label = (self.metric + '  ')[:width]
        result = Text(label, no_wrap=True, overflow='crop')
        remaining = width - len(label)
        if not self.valid:
            result.append('n/a'[:remaining], style='yellow')
            return result
        if self.total == 0:
            result.append('0 B · nessuna memoria'.center(remaining)[:remaining], style='grey70 on #30363d')
            return result
        counts = cell_widths([p.value for p in self.parts], self.total, remaining)
        for part, count in zip(self.parts, counts):
            caption = part.short.center(count) if count >= len(part.short) + 2 else ' ' * count
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
        return Measurement(min(len(self.metric) + 2, options.max_width), options.max_width)
