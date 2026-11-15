"""Signed change on a symmetric, explicitly labelled scale."""
from rich.text import Text
from textual.widgets import Static


class DeltaBar(Static):
    DEFAULT_CSS = 'DeltaBar { height: 1; }'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.delta: int | None = None
        self.scale: int | None = None

    def set_values(self, delta: int | None, scale: int | None) -> None:
        self.delta, self.scale = delta, scale
        self.refresh()

    def render(self) -> Text:
        width = self.content_size.width
        if self.delta is None or self.scale is None:
            return Text('Δ n/a', style='yellow')
        if self.scale <= 0 or width < 3:
            return Text('Δ 0 B' if self.delta == 0 else 'Δ n/a', style='grey70')
        middle = width // 2
        span = min(middle, width-middle-1)
        length = min(span, abs(self.delta) * span // self.scale)
        cells = [' '] * width
        cells[middle] = '│'
        if self.delta < 0:
            cells[middle-length:middle] = ['◀'] * length
        elif self.delta > 0:
            cells[middle+1:middle+1+length] = ['▶'] * length
        result = Text(''.join(cells), no_wrap=True, overflow='crop')
        if length:
            result.stylize('red' if self.delta < 0 else 'green',
                           middle-length if self.delta < 0 else middle+1,
                           middle if self.delta < 0 else middle+1+length)
        return result
