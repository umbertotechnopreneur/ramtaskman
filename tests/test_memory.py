import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from ramtaskman.backends.linux import LinuxBackend, parse_rollup, read_system
from ramtaskman.models import ProcessMemory, Snapshot, SystemMemory
from ramtaskman.report import to_dict

K = 1024
ROLLUP = '''00400000-7fffffffffff ---p 00000000 00:00 0 [rollup]
Rss: 100 kB
Pss: 70 kB
Private_Clean: 10 kB
Private_Dirty: 30 kB
Shared_Clean: 60 kB
Swap: 8 kB
SwapPss: 4 kB
'''


def fixture() -> Snapshot:
    # Deliberately synthetic and portable: suitable for UI captures.
    system = SystemMemory(16 << 30, 10 << 30, 6 << 30, 4 << 30, 300 << 20,
                          4 << 30, 600 << 20, 18.0, 0.2)
    system.segments = dict(anon=5 << 30, file_cache=3840 << 20, shmem=256 << 20,
                           buffers=56 << 20, slab_reclaimable=200 << 20,
                           slab_unreclaimable=100 << 20, other=668 << 20, free=6 << 30)
    rows = [
        ProcessMemory(100, 10, 'browser', 1000, '/demo/browser', 900 << 20, 600 << 20, 400 << 20, 40 << 20, 20 << 20),
        ProcessMemory(101, 11, 'browser-worker', 1000, '/demo/browser', 300 << 20, 200 << 20, 100 << 20, 0, 0),
        ProcessMemory(200, 20, 'editor', 1000, '/demo/editor', 500 << 20, 450 << 20, 400 << 20, 0, 0),
        ProcessMemory(300, 30, 'protected', 0, None, 100 << 20, reason='smaps_rollup: accesso negato'),
    ]
    return Snapshot(1700000000, system, rows, 25, 1)


class AccountingTests(unittest.TestCase):
    def test_unix_executable_name_preserves_backslash(self):
        snap = fixture()
        snap.processes = [ProcessMemory(1, 1, 'demo', 1000, '/demo/name\\literal', uss=0)]
        self.assertEqual(snap.applications[0].name, 'name\\literal')

    def test_pss_uss_and_swap_are_distinct(self):
        values = parse_rollup(ROLLUP)
        self.assertEqual(values, dict(rss=100*K, pss=70*K, uss=40*K, swap=8*K, swap_pss=4*K))

    def test_missing_is_not_measured_zero(self):
        self.assertIsNone(parse_rollup('Rss: 0 kB\n')['pss'])
        self.assertEqual(parse_rollup('Pss: 0 kB\n')['pss'], 0)
        self.assertIsNone(parse_rollup('Private_Clean: 0 kB\n')['uss'])

    def test_grouping_uses_executable_and_user_not_process_name(self):
        snap = fixture()
        snap.processes.append(ProcessMemory(400, 40, 'browser', 0, '/demo/browser', pss=10))
        self.assertEqual(len(snap.applications), 4)
        browser = next(a for a in snap.applications if a.uid == 1000 and a.name == 'browser')
        self.assertEqual(browser.total('pss'), 800 << 20)
        self.assertEqual(browser.total('uss'), 500 << 20)

    def test_incomplete_group_does_not_claim_complete_total(self):
        snap = fixture()
        snap.processes[1].pss = None
        app = snap.applications[0]
        self.assertIsNone(app.total('pss'))
        self.assertEqual(app.measured, 1)
        self.assertEqual(app.total('swap'), 40 << 20)

    def test_no_readable_pss_is_none_including_json(self):
        snap = fixture()
        for proc in snap.processes:
            proc.pss = None
        output = json.loads(json.dumps(to_dict(snap)))
        self.assertIsNone(output['visible_pss_bytes'])
        self.assertTrue(output['visible_pss_is_partial'])
        self.assertIsNone(output['applications'][0]['pss'])

    def test_partial_visible_sum_is_not_global_used(self):
        snap = fixture()
        self.assertEqual(snap.visible_sum('pss'), 1250 << 20)
        self.assertNotEqual(snap.visible_sum('pss'), snap.system.used)
        self.assertEqual(to_dict(snap)['system']['used'], 6 << 30)

    def test_pid_reuse_has_different_key(self):
        a = ProcessMemory(5, 1, 'x', 1, None)
        b = ProcessMemory(5, 2, 'x', 1, None)
        self.assertNotEqual(a.key, b.key)

    def test_system_cache_is_not_added_to_used(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'meminfo').write_text('MemTotal: 100 kB\nMemAvailable: 60 kB\nMemFree: 10 kB\n'
                                       'Cached: 50 kB\nBuffers: 5 kB\nSReclaimable: 10 kB\nShmem: 5 kB\n'
                                       'SwapTotal: 20 kB\nSwapFree: 12 kB\n')
            system = read_system(root)
            self.assertEqual(system.used, 40*K)
            self.assertEqual(system.cache, 60*K)
            self.assertEqual(system.swap_used, 8*K)
            self.assertIsNone(system.pressure_percent)

    def test_process_exits_during_sample_is_not_retained(self):
        process = Mock(pid=99)
        process.create_time.return_value = 1
        process._proc.name.return_value = 'gone'
        process._proc.exe.return_value = '/demo/gone'
        process.uids.return_value = Mock(real=1000)
        process.memory_info.return_value = Mock(rss=10)
        process.is_running.return_value = False
        with tempfile.TemporaryDirectory() as directory:
            self.assertIsNone(LinuxBackend(Path(directory)).read_process(process))

    def test_protected_process_keeps_rss_and_unknown_pss(self):
        from unittest.mock import patch
        process = Mock(pid=99)
        process.create_time.return_value = 1
        process._proc.name.return_value = 'protected'
        process._proc.exe.return_value = '/demo/protected'
        process.uids.return_value = Mock(real=0)
        process.memory_info.return_value = Mock(rss=1234)
        process.is_running.return_value = True
        with patch.object(Path, 'read_text', side_effect=PermissionError):
            row = LinuxBackend().read_process(process)
        self.assertEqual(row.rss, 1234)
        self.assertIsNone(row.pss)
        self.assertIn('accesso negato', row.reason)
