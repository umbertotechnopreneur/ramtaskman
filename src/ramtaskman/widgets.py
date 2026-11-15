"""Drawing helpers from gputaskman (Scott Hanselman, MIT)."""
from rich.text import Text

SPARK = "▁▂▃▄▅▆▇█"

def spark(values, width: int = 30, top: float = 100.0) -> str:
    vals = list(values)[-width:]
    return "".join(
        SPARK[min(max(int(v / top * (len(SPARK) - 1) + 0.5), 0), len(SPARK) - 1)]
        if v is not None else " "
        for v in vals
    )

def stacked_bar(parts: list[tuple[float, str]], total: float, width: int) -> Text:
    t = Text()
    used = 0
    for value, style in parts:
        n = int(round(value / total * width)) if total else 0
        n = min(n, width - used)
        if n > 0:
            t.append("█" * n, style=style)
            used += n
    t.append("░" * (width - used), style="grey27")
    return t
