"""Standalone offline region viewer: never constructs a collector or provider."""
from textual.app import App

from .models import ProcessMemory
from .region_screen import RegionScreen


class ReplayApp(App):
    TITLE = 'ramtaskman · acquisizione salvata'

    def __init__(self, current, baseline=None, *, language: str = 'it') -> None:
        super().__init__()
        self.current, self.baseline = current, baseline
        self.language = language

    def on_mount(self) -> None:
        c = self.current
        process = ProcessMemory(c.pid, c.started_at, c.name, None, c.executable_identity)
        self.push_screen(RegionScreen(process, c.platform, offline_capture=c,
                                      offline_baseline=self.baseline), callback=lambda _: self.exit())
