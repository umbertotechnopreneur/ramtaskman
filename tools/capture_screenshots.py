"""Capture deterministic SYNTHETIC fixtures; no local process names or paths."""
import asyncio
import os
from time import time

# CI/tool shells may disable color; captures intentionally show the terminal palette.
os.environ.pop("NO_COLOR", None)
os.environ["FORCE_COLOR"] = "1"
import sys
from pathlib import Path

from ramtaskman.app import RamTaskManager
from ramtaskman.models import LinuxSystemMemory

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tests'))
from test_memory import fixture
from test_region_ui import FakeReader


class DemoReader(FakeReader):
    def read(self, process, cancelled=None):
        snap = super().read(process, cancelled)
        if self.calls > 1:
            snap.regions[1].rss += 30 << 20
        return snap


def demo_snapshot():
    snap = fixture()
    snap.taken = time()
    snap.system.linux_details = LinuxSystemMemory(commit_total=7 << 30, commit_limit=20 << 30)
    for proc in snap.processes[:2]:
        proc.app_id = '/user.slice/user-1000.slice/user@1000.service/app.slice/app-org.example.Browser-42.scope'
        proc.app_name = 'org.example.Browser'
        proc.app_source = 'systemd-cgroup'
        proc.breakdown = dict(pss_anon=proc.pss * 3 // 4, pss_file=proc.pss // 4,
                              pss_shmem=0, private_clean=proc.uss // 4,
                              private_dirty=proc.uss * 3 // 4, shared_clean=proc.rss-proc.uss,
                              shared_dirty=0, anonymous=proc.uss, lazy_free=0, anon_huge_pages=0)
    snap.processes[1].executable = '/demo/renderer'
    return snap


async def main():
    output = Path('captures')
    output.mkdir(exist_ok=True)
    app = RamTaskManager(live=False, region_reader=DemoReader())
    async with app.run_test(size=(160, 48)) as pilot:
        for _ in range(30):
            app.apply(demo_snapshot())
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
    for language in ('it', 'en', 'zh', 'ko', 'fr', 'vi'):
        localized = RamTaskManager(live=False, language=language)
        async with localized.run_test(size=(160, 48)) as pilot:
            localized.apply(demo_snapshot())
            await pilot.pause()
            localized.save_screenshot(f'language-{language}.svg', path=str(output))
    print('Synthetic screenshots: captures/ (not live measurements).')


if __name__ == '__main__':
    asyncio.run(main())
