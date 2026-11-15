"""Windows/macOS API contracts simulated on any host; not hardware validation."""
import json
import unittest
from types import SimpleNamespace as NS
from unittest.mock import Mock, patch

import psutil

from ramtaskman.backends.psutil_backend import PsutilBackend
from ramtaskman.collector import Collector, make_backend
from ramtaskman.models import ProcessMemory
from ramtaskman.report import to_dict
from test_memory import fixture


def process():
    p = Mock(pid=42)
    p.create_time.return_value = 100.0
    p.name.return_value = 'editor.exe'
    p.username.return_value = 'DOMAIN\\alice'
    p.uids.return_value = NS(real=501)
    p.exe.return_value = 'C:\\Apps\\Editor.exe'
    p.memory_info.return_value = NS(rss=1000, vms=9000, private=8000, pagefile=7000)
    p.memory_full_info.return_value = NS(rss=1000, uss=600, vms=9000, private=8000, pagefile=7000)
    p.is_running.return_value = True
    return p


class BackendTests(unittest.TestCase):
    def test_selects_backend_without_importing_foreign_native_libraries(self):
        for platform, expected in (('linux', 'linux'), ('win32', 'windows'), ('darwin', 'macos')):
            self.assertEqual(make_backend(platform).name, expected)
        with self.assertRaises(RuntimeError):
            make_backend('unsupported')

    def test_windows_uss_is_not_commit_and_swap_is_not_pagefile(self):
        row = PsutilBackend('windows').read_process(process())
        self.assertEqual(row.rss, 1000)
        self.assertEqual(row.uss, 600)
        self.assertEqual(row.user, 'DOMAIN\\alice')
        self.assertIsNone(row.uid)
        for metric in ('pss', 'swap', 'swap_pss'):
            self.assertIsNone(getattr(row, metric))

    def test_windows_access_denied_degrades_to_rss_without_fake_uss(self):
        p = process()
        p.memory_full_info.side_effect = psutil.AccessDenied(42)
        row = PsutilBackend('windows').read_process(p)
        self.assertEqual(row.rss, 1000)
        self.assertIsNone(row.uss)
        self.assertIn('accesso negato', row.reason)

    def test_mac_uses_uid_and_retains_missing_metrics(self):
        p = process()
        p.exe.return_value = '/Applications/Editor.app/Contents/MacOS/Editor'
        row = PsutilBackend('macos').read_process(p)
        self.assertEqual(row.uid, 501)
        self.assertEqual(row.uss, 600)
        self.assertIsNone(row.pss)
        self.assertIsNone(row.swap)
        p.username.assert_not_called()

    def test_terminated_windows_process_is_discarded(self):
        p = process()
        p.is_running.return_value = False
        self.assertIsNone(PsutilBackend('windows').read_process(p))

    def test_global_swap_failure_does_not_erase_ram(self):
        with patch('psutil.virtual_memory', return_value=NS(total=1000, available=600, free=600)), \
             patch('psutil.swap_memory', side_effect=OSError):
            system = PsutilBackend('windows').read_system()
        self.assertEqual(system.used, 400)
        self.assertIsNone(system.swap_used)
        self.assertIsNone(system.swap_total)
        self.assertIsNone(system.cache)
        self.assertIsNone(system.pressure_percent)
        self.assertTrue(system.notes)

    def test_windows_owners_and_unknown_owner_are_never_combined(self):
        snap = fixture()
        snap.processes = [
            ProcessMemory(1, 1, 'app', None, 'c:\\app.exe', user='DOMAIN\\alice'),
            ProcessMemory(2, 2, 'app', None, 'c:\\app.exe', user='DOMAIN\\bob'),
            ProcessMemory(3, 3, 'app', None, 'c:\\app.exe'),
            ProcessMemory(4, 4, 'app', None, 'c:\\app.exe'),
        ]
        self.assertEqual(len(snap.applications), 4)
        self.assertEqual(snap.applications[0].name, 'app.exe')

    def test_windows_paths_are_case_normalized(self):
        a, b = process(), process()
        b.pid = 43
        b.exe.return_value = 'c:\\apps\\EDITOR.EXE'
        backend = PsutilBackend('windows')
        snap = fixture()
        snap.processes = [backend.read_process(a), backend.read_process(b)]
        self.assertEqual(len(snap.applications), 1)
        self.assertEqual(snap.applications[0].total('uss'), 1200)

    def test_collector_reports_backend_capabilities_and_json_nulls(self):
        backend = PsutilBackend('windows')
        with patch('psutil.virtual_memory', return_value=NS(total=10000, available=6000, free=6000)), \
             patch('psutil.swap_memory', return_value=NS(total=2000, used=50)), \
             patch('psutil.process_iter', return_value=[process()]), \
             patch('psutil.cpu_percent', return_value=10):
            collector = Collector(backend=backend)
            first = collector.sample()
            second = collector.sample()
        self.assertIsNone(first.system.cpu_percent)
        self.assertEqual(second.system.cpu_percent, 10)
        output = json.loads(json.dumps(to_dict(second)))
        self.assertEqual(output['platform'], 'windows')
        self.assertEqual(output['coverage']['uss'], 1)
        self.assertIn('pss', output['unsupported'])
        self.assertIsNone(output['processes'][0]['swap'])
        self.assertIsNone(output['applications'][0]['pss'])
        self.assertEqual(output['system']['swap_used'], 50)
