"""Synthetic mappings and procfs failures, independent of host permissions."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import psutil

from ramtaskman.models import ProcessMemory
from ramtaskman.regions import LinuxRegionReader, RegionSnapshot, classify_region, parse_smaps

K = 1024
FIRST = '''00400000-00410000 r-xp 00002000 08:01 42 /demo/my app (deleted)
Size: 64 kB
Rss: 40 kB
Pss: 30 kB
Private_Clean: 4 kB
Private_Dirty: 16 kB
Shared_Clean: 20 kB
Shared_Dirty: 0 kB
Anonymous: 16 kB
Swap: 8 kB
SwapPss: 4 kB
Private_Hugetlb: 2048 kB
Shared_Hugetlb: 0 kB
KernelPageSize: 4 kB
MMUPageSize: 4 kB
THPeligible: 0
VmFlags: rd ex mr mw me sd
'''
SECOND = '''01000000-01004000 rw-p 00000000 00:00 0 [heap]
Size: 16 kB
Rss: 0 kB
Private_Clean: 0 kB
VmFlags: rd wr mr mw me ac sd
'''


def identity():
    return ProcessMemory(100, 123.0, 'demo', 1000, '/demo/my app')


class ParseRegionsTests(unittest.TestCase):
    def test_fields_paths_units_flags_and_hugetlb_are_distinct(self):
        regions = parse_smaps(FIRST + SECOND, '/demo/my app')
        first, second = regions
        self.assertEqual(first.key, '400000-410000')
        self.assertEqual(first.size, 64*K)
        self.assertEqual(first.permissions, 'r-xp')
        self.assertEqual(first.offset, 0x2000)
        self.assertEqual(first.device, '08:01')
        self.assertEqual(first.inode, 42)
        self.assertEqual(first.path, '/demo/my app (deleted)')
        self.assertEqual(first.category, 'executable')
        self.assertEqual((first.rss, first.pss, first.uss, first.swap, first.swap_pss),
                         (40*K, 30*K, 20*K, 8*K, 4*K))
        self.assertEqual(first.breakdown['private_hugetlb'], 2048*K)
        self.assertEqual(first.breakdown['anonymous'], 16*K)
        self.assertIn('ex', first.vm_flags)
        self.assertEqual(second.rss, 0)
        self.assertIsNone(second.pss)
        self.assertIsNone(second.uss)
        self.assertIsNone(second.swap)
        self.assertEqual(second.breakdown['private_clean'], 0)
        self.assertIsNone(second.breakdown['private_dirty'])

    def test_region_origin_does_not_claim_contents_or_guess_heaps(self):
        cases = {
            '': 'anonymous', '[anon:allocator]': 'anonymous', '[heap]': 'heap',
            '[stack]': 'stack', '[stack:99]': 'stack', '[vdso]': 'special',
            '[vvar_vclock]': 'special', '[anon_shmem:cache]': 'shmem',
            '/dev/shm/example': 'shmem', '/memfd:demo (deleted)': 'shmem',
            '/SYSV00000000 (deleted)': 'shmem', '/demo/liba.so.1': 'library',
            '/demo/data.bin': 'file', '/demo/app': 'executable',
        }
        for path, expected in cases.items():
            with self.subTest(path=path):
                self.assertEqual(classify_region(path, '/demo/app'), expected)
        # CoW anonymous pages do not change a file's mapping-origin category.
        first = parse_smaps(FIRST)[0]
        self.assertEqual(first.category, 'file')
        self.assertEqual(first.breakdown['anonymous'], 16*K)

    def test_invalid_counts_duplicates_ranges_or_size_fail_explicitly(self):
        for text in (
            FIRST.replace('Pss: 30 kB', 'Pss: -1 kB'),
            FIRST.replace('Pss: 30 kB', 'Pss: unknown kB'),
            FIRST + 'Pss: 4 kB\n',
            FIRST.replace('Size: 64 kB', 'Size: 128 kB'),
            FIRST.replace('00400000-00410000', '00410000-00400000'),
            FIRST + FIRST,
            'Rss: 1 kB\n',
        ):
            with self.subTest(text=text[:100]):
                with self.assertRaises(ValueError):
                    parse_smaps(text)

    def test_totals_require_complete_scan_and_all_fields(self):
        snap = RegionSnapshot(100, 123, 'demo', 0, parse_smaps(FIRST + SECOND))
        self.assertEqual(snap.total('rss'), 40*K)
        self.assertEqual(snap.total('size'), 80*K)
        self.assertIsNone(snap.total('pss'))
        snap.complete = False
        self.assertIsNone(snap.total('rss'))


class ReadRegionsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / '100').mkdir()
        self.path = self.root / '100' / 'smaps'
        # Byte budgets describe procfs bytes, including its LF line endings.
        # Binary writes keep the fixture identical on Windows and Unix hosts.
        self.path.write_bytes((FIRST + SECOND).encode('utf-8'))
        self.proc = Mock()
        self.proc.create_time.return_value = 123.0
        self.proc.is_running.return_value = True
        self.proc._proc.exe.return_value = '/demo/my app'
        for public in (self.proc.name, self.proc.exe, self.proc.cmdline):
            public.side_effect = AssertionError('public process metadata fallback is forbidden')
        self.psutil = patch('ramtaskman.regions.psutil.Process', return_value=self.proc).start()
        self.addCleanup(patch.stopall)

    def test_complete_scan_verifies_identity_before_and_after_and_measures_time(self):
        snap = LinuxRegionReader(self.root).read(identity())
        self.assertTrue(snap.complete)
        self.assertIsNone(snap.reason)
        self.assertEqual(len(snap.regions), 2)
        self.assertGreaterEqual(snap.sample_ms, 0)
        self.assertEqual((snap.pid, snap.started_at, snap.name), (100, 123.0, 'demo'))
        self.assertEqual(snap.executable_identity, '/demo/my app')
        self.assertEqual(self.psutil.call_count, 2)

    def test_exec_change_or_unreadable_image_does_not_claim_same_identity(self):
        self.proc._proc.exe.side_effect = ['/demo/my app', '/demo/other']
        snap = LinuxRegionReader(self.root).read(identity())
        self.assertFalse(snap.complete)
        self.assertEqual(snap.regions, [])
        self.proc._proc.exe.side_effect = psutil.AccessDenied(100)
        snap = LinuxRegionReader(self.root).read(identity())
        self.assertTrue(snap.complete)
        self.assertIsNone(snap.executable_identity)

    def test_pid_reused_before_or_after_scan_discards_every_region(self):
        for times in ([999.0], [123.0, 999.0]):
            with self.subTest(times=times):
                self.proc.create_time.side_effect = times
                snap = LinuxRegionReader(self.root).read(identity())
                self.assertFalse(snap.complete)
                self.assertEqual(snap.regions, [])
                self.assertIn('PID riutilizzato', snap.reason)

    def test_terminated_process_and_permission_failure_have_no_stale_data(self):
        for exception in (psutil.NoSuchProcess(100), psutil.AccessDenied(100)):
            self.psutil.side_effect = exception
            snap = LinuxRegionReader(self.root).read(identity())
            self.assertFalse(snap.complete)
            self.assertEqual(snap.regions, [])
            self.assertTrue(snap.reason)
        self.psutil.side_effect = None
        with patch.object(Path, 'open', side_effect=PermissionError):
            snap = LinuxRegionReader(self.root).read(identity())
        self.assertIn('accesso negato', snap.reason)
        self.assertFalse(snap.complete)
        self.assertEqual(snap.regions, [])
        self.proc.is_running.return_value = False
        self.assertEqual(LinuxRegionReader(self.root).read(identity()).regions, [])

    def test_byte_limit_keeps_only_closed_regions_and_never_claims_total(self):
        cap = len(FIRST.encode()) + len(SECOND.splitlines(keepends=True)[0].encode()) + 2
        snap = LinuxRegionReader(self.root, max_bytes=cap).read(identity())
        self.assertFalse(snap.complete)
        self.assertEqual(len(snap.regions), 1)
        self.assertIn('Limite di lettura', snap.reason)
        self.assertIsNone(snap.total('rss'))
        # Budget stopping in the first region must not expose truncated metrics.
        snap = LinuxRegionReader(self.root, max_bytes=100).read(identity())
        self.assertFalse(snap.complete)
        self.assertEqual(snap.regions, [])

    def test_region_limit_and_exact_byte_budget(self):
        snap = LinuxRegionReader(self.root, max_regions=1).read(identity())
        self.assertFalse(snap.complete)
        self.assertEqual(len(snap.regions), 1)
        self.assertIn('Limite di regioni', snap.reason)
        snap = LinuxRegionReader(self.root, max_bytes=len((FIRST + SECOND).encode())).read(identity())
        self.assertTrue(snap.complete)
        self.assertEqual(len(snap.regions), 2)

    def test_cancellation_before_scan_and_during_second_region(self):
        snap = LinuxRegionReader(self.root).read(identity(), cancelled=lambda: True)
        self.assertFalse(snap.complete)
        self.assertEqual(snap.regions, [])
        self.psutil.assert_not_called()
        calls = 0

        def cancelled():
            nonlocal calls
            calls += 1
            # Initial check, all first-region lines, second header, then stop.
            return calls > len(FIRST.splitlines()) + 2

        snap = LinuxRegionReader(self.root).read(identity(), cancelled)
        self.assertFalse(snap.complete)
        self.assertIn('annullata', snap.reason)
        self.assertEqual(len(snap.regions), 1)

    def test_time_limit_and_bad_input_are_explicit(self):
        clock = iter((0, 0, 4, 4, 4))
        with patch('ramtaskman.regions.time.monotonic', side_effect=lambda: next(clock)):
            snap = LinuxRegionReader(self.root, max_seconds=3).read(identity())
        self.assertFalse(snap.complete)
        self.assertIn('Limite di tempo', snap.reason)
        self.assertEqual(snap.regions, [])
        self.path.write_bytes((FIRST + SECOND.replace('Rss: 0 kB', 'Rss: bad kB')).encode('utf-8'))
        snap = LinuxRegionReader(self.root).read(identity())
        self.assertFalse(snap.complete)
        self.assertEqual(snap.regions, [])
        self.assertIn('contatore smaps non valido', snap.reason)

    def test_empty_maps_and_missing_procfs_are_distinct(self):
        self.path.write_bytes(b'')
        snap = LinuxRegionReader(self.root).read(identity())
        self.assertTrue(snap.complete)
        self.assertEqual(snap.regions, [])
        self.path.unlink()
        snap = LinuxRegionReader(self.root).read(identity())
        self.assertFalse(snap.complete)
        self.assertTrue(snap.reason)


if __name__ == '__main__':
    unittest.main()
