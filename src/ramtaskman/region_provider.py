"""Region providers and capabilities; loading native libraries remains lazy."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Callable
import time

from .models import ProcessMemory
from .regions import LinuxRegionReader, RegionSnapshot


@dataclass(frozen=True)
class RegionCapabilities:
    platform: str
    source: str
    supported: bool
    virtual: bool = False
    rss: bool = False
    pss: bool = False
    uss: bool = False
    swap: bool = False
    swap_pss: bool = False
    explanation: str = ''


class RegionProvider(Protocol):
    capabilities: RegionCapabilities

    def read(self, process: ProcessMemory,
             cancelled: Callable[[], bool] | None = None) -> RegionSnapshot: ...


class LinuxProvider:
    capabilities = RegionCapabilities('linux', 'Linux smaps', True, True, True, True,
                                      True, True, True)

    def __init__(self, reader: LinuxRegionReader | None = None) -> None:
        self.reader = reader if reader is not None else LinuxRegionReader()

    def read(self, process: ProcessMemory,
             cancelled: Callable[[], bool] | None = None) -> RegionSnapshot:
        return self.reader.read(process, cancelled)


class UnsupportedProvider:
    def __init__(self, platform: str, explanation: str | None = None) -> None:
        self.capabilities = RegionCapabilities(platform, 'n/a', False,
            explanation=explanation or f'Mappa per regioni non implementata su {platform}.')

    def read(self, process: ProcessMemory,
             cancelled: Callable[[], bool] | None = None) -> RegionSnapshot:
        return RegionSnapshot(process.pid, process.started_at, process.name, time.time(),
                              reason=self.capabilities.explanation, complete=False)


def make_region_provider(platform: str) -> RegionProvider:
    if platform.startswith('linux'):
        return LinuxProvider()
    if platform in ('windows', 'win32'):
        from .backends.windows_regions import WindowsRegionProvider
        return WindowsRegionProvider()
    if platform in ('macos', 'darwin'):
        return UnsupportedProvider('macos')
    return UnsupportedProvider(platform)
