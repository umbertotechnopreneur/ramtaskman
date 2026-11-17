"""Capture deterministic SYNTHETIC fixtures; no local process names or paths."""
import asyncio
import json
import math
import os
from time import time

# CI/tool shells may disable color; captures intentionally show the terminal palette.
os.environ.pop("NO_COLOR", None)
os.environ["FORCE_COLOR"] = "1"
import sys
from pathlib import Path

from ramtaskman.app import RamTaskManager
from ramtaskman.models import LinuxSystemMemory, ProcessMemory
from ramtaskman.i18n import LANGUAGES

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tests'))
from test_memory import fixture
from test_region_ui import FakeReader


class DemoReader(FakeReader):
    def read(self, process, cancelled=None):
        snap = super().read(process, cancelled)
        if self.calls > 1:
            for metric in ('rss', 'pss', 'uss'):
                setattr(snap.regions[1], metric, getattr(snap.regions[1], metric) + (30 << 20))
            snap.regions[1].breakdown['private_dirty'] += 30 << 20
        return snap


def demo_snapshot(step=59):
    snap = fixture()
    snap.taken = time()
    snap.system.linux_details = LinuxSystemMemory(commit_total=7 << 30, commit_limit=20 << 30)
    for proc in snap.processes[:2]:
        proc.app_id = '/user.slice/user-1000.slice/user@1000.service/app.slice/app-org.example.Browser-42.scope'
        proc.app_name = 'Browser'
        proc.app_source = 'systemd-cgroup'
        proc.breakdown = dict(pss_anon=proc.pss * 3 // 4, pss_file=proc.pss // 4,
                              pss_shmem=0, private_clean=proc.uss // 4,
                              private_dirty=proc.uss * 3 // 4, shared_clean=proc.rss-proc.uss,
                              shared_dirty=0, anonymous=proc.uss, lazy_free=0, anon_huge_pages=0)
    snap.processes[1].executable = '/demo/renderer'
    for index, (name, mib) in enumerate((('notebook', 380), ('build-worker', 260),
                                        ('media-player', 180), ('terminal', 95),
                                        ('index-worker', 65))):
        snap.processes.append(ProcessMemory(400 + index, 40 + index, name, 1000,
                                            f'/demo/{name}', (mib + 50) << 20,
                                            mib << 20, (mib - 25) << 20, 0, 0))
    # A deterministic sequence, not a benchmark or a trace of the host computer.
    delta = int(700 * math.sin(step / 10)) << 20
    snap.system.available += delta
    snap.system.free += delta
    snap.system.segments['anon'] -= delta
    snap.system.segments['free'] += delta
    return snap


def save_capture(app, output, name, *, selector=None):
    """Keep the original SVG and measured crop bounds separately from presentation."""
    app.save_screenshot(f'{name}.svg', path=str(output))
    region = app.screen.query_one(selector).region if selector else app.screen.region
    (output / f'{name}.json').write_text(json.dumps({
        'columns': app.size.width, 'rows': app.size.height,
        'crop': [region.x, region.y, region.width, region.height],
        'synthetic': True, 'platform': 'linux',
    }, indent=2) + '\n', encoding='utf-8')
    print(f'Synthetic capture: {name}', flush=True)


async def capture_gallery(output):
    """Public views use English and ordinary app layouts; no screenshot-only CSS."""
    app = RamTaskManager(live=False, region_reader=DemoReader(), language='en')
    async with app.run_test(size=(120, 42)) as pilot:
        for step in range(60):
            app.apply(demo_snapshot(step))
        await pilot.pause()
        save_capture(app, output, 'gallery-overview')
        await pilot.resize_terminal(160, 64)
        await pilot.press('m')
        await pilot.pause()
        save_capture(app, output, 'gallery-full', selector='#device')
        await pilot.press('m', 'enter')
        await pilot.pause()
        await pilot.press('r')
        await app.workers.wait_for_complete()
        await pilot.pause()
        save_capture(app, output, 'gallery-regions')
        await pilot.press('b', 'r')
        await app.workers.wait_for_complete()
        await pilot.pause()
        await pilot.press('c')
        await app.workers.wait_for_complete()
        await pilot.pause()
        save_capture(app, output, 'gallery-comparison')
        await pilot.press('escape')
        await pilot.pause()


async def main():
    output = Path('captures')
    output.mkdir(exist_ok=True)
    app = RamTaskManager(live=False, region_reader=DemoReader())
    async with app.run_test(size=(160, 48)) as pilot:
        for step in range(60):
            app.apply(demo_snapshot(step))
        await pilot.pause()
        app.save_screenshot('overview.svg', path=str(output))
        await pilot.press('m')
        await pilot.pause()
        app.save_screenshot('full-diagnostics.svg', path=str(output))
        await pilot.press('m')
        await pilot.pause()
        await pilot.press('enter')
        await pilot.pause()
        app.save_screenshot('processes.svg', path=str(output))
        await pilot.press('d')
        await pilot.pause()
        app.save_screenshot('detail.svg', path=str(output))
        await pilot.press('escape', 'r')
        await app.workers.wait_for_complete()
        await pilot.pause()
        app.save_screenshot('regions-resident.svg', path=str(output))
        await pilot.press('v')
        await pilot.pause()
        app.save_screenshot('regions-virtual.svg', path=str(output))
        await pilot.press('b', 'r')
        await app.workers.wait_for_complete()
        await pilot.press('c')
        await app.workers.wait_for_complete()
        await pilot.pause()
        app.save_screenshot('regions-comparison.svg', path=str(output))
        await pilot.press('c')
        await pilot.resize_terminal(80, 24)
        await pilot.pause()
        app.save_screenshot('regions-narrow.svg', path=str(output))
        await pilot.resize_terminal(160, 48)
        await pilot.press('escape', 'escape', 'slash')
        from textual.widgets import Input, Select
        app.query_one('#search', Input).value = 'renderer'
        app.query_one('#memory-filter', Select).value = 'swap'
        await pilot.pause()
        app.save_screenshot('filters.svg', path=str(output))
        await pilot.press('escape', 'question_mark')
        await pilot.pause()
        app.save_screenshot('help.svg', path=str(output))
    # Each panel is a real Textual render of the same synthetic sample in its locale.
    for language in LANGUAGES:
        localized = RamTaskManager(live=False, language=language)
        async with localized.run_test(size=(160, 48)) as pilot:
            localized.apply(demo_snapshot())
            await pilot.pause()
            localized.save_screenshot(f'language-{language}.svg', path=str(output))
            save_capture(localized, output, f'gallery-language-{language}', selector='#device')
    await capture_gallery(output)
    print('Synthetic screenshots: captures/ (not live measurements).')


if __name__ == '__main__':
    asyncio.run(main())
