"""Fair budget is opt-in, never caches counters, and preserves group completeness."""
import unittest
from unittest.mock import patch

import psutil

from ramtaskman.collector import Collector
from ramtaskman.models import ProcessMemory, SystemMemory
from ramtaskman.report import to_dict
from ramtaskman.detail import breakdown_total, detail_bars


class FakeProcess:
    def __init__(self, pid):
        self.pid = pid


class Backend:
    name = 'linux'
    source = 'synthetic'
    unsupported = {}

    def __init__(self):
        self.attempts = []
        self.bad_identity = set()
        self.bad_metrics = set()

    def read_system(self):
        return SystemMemory(1000, 500, 100, None, None, None, None)

    def read_identity(self, proc):
        if proc.pid in self.bad_identity:
            raise psutil.AccessDenied(proc.pid)
        return ProcessMemory(proc.pid, proc.pid + 1., 'test', 1000, '/synthetic/app')

    def read_metrics(self, proc, row):
        self.attempts.append(proc.pid)
        if proc.pid in self.bad_metrics:
            raise psutil.NoSuchProcess(proc.pid)
        row.rss = row.pss = row.uss = proc.pid
        row.swap = row.swap_pss = 0
        row.breakdown = dict(pss_anon=proc.pid, pss_file=0, pss_shmem=0,
                             private_clean=proc.pid, private_dirty=0, shared_clean=0, shared_dirty=0)
        return row


class BudgetTests(unittest.TestCase):
    def sample(self, collector, count=5):
        with patch('ramtaskman.collector.psutil.process_iter', return_value=[FakeProcess(i) for i in range(1, count + 1)]), \
             patch('ramtaskman.collector.psutil.cpu_percent', return_value=0):
            return collector.sample()

    def test_budget_rotates_fairly_and_never_reuses_old_metrics(self):
        backend = Backend()
        collector = Collector(backend=backend, max_measurements=2)
        first = self.sample(collector)
        second = self.sample(collector)
        third = self.sample(collector)
        self.assertEqual(backend.attempts, [1, 2, 3, 4, 1, 5])
        self.assertTrue(first.enumeration_complete)
        self.assertEqual(first.measurement_attempted, 2)
        self.assertEqual(first.measurement_deferred, 3)
        self.assertEqual(len(first.processes), 5)
        self.assertIsNone(first.applications[0].total('pss'))
        self.assertEqual(second.processes[0].reason, 'Misura rinviata: budget di campionamento')
        self.assertIsNone(second.processes[0].pss)
        self.assertEqual(third.processes[0].pss, 1)
        self.assertTrue(to_dict(first)['visible_pss_is_partial'])

    def test_identity_missing_invalidates_group_aggregates_even_if_others_complete(self):
        backend = Backend()
        backend.bad_identity.add(3)
        snap = self.sample(Collector(backend=backend, max_measurements=9))
        self.assertFalse(snap.enumeration_complete)
        self.assertEqual(snap.skipped, 1)
        group = snap.applications[0]
        self.assertEqual(len(group.processes), 4)
        self.assertFalse(group.membership_complete)
        self.assertIsNone(group.total('rss'))
        self.assertIsNone(breakdown_total(group, 'pss_anon')[0])
        self.assertFalse(detail_bars(group)[0].valid)

    def test_process_dies_after_identity_prevents_complete_group(self):
        backend = Backend()
        backend.bad_metrics.add(2)
        snap = self.sample(Collector(backend=backend, max_measurements=5))
        self.assertFalse(snap.enumeration_complete)
        self.assertEqual(snap.skipped, 1)
        self.assertIsNone(snap.applications[0].total('uss'))

    def test_fairness_cursor_survives_insertions_before_prior_position(self):
        backend = Backend()
        collector = Collector(backend=backend, max_measurements=1)
        self.sample(collector, count=3)
        with patch('ramtaskman.collector.psutil.process_iter', return_value=[FakeProcess(0), FakeProcess(1), FakeProcess(2), FakeProcess(3)]), \
             patch('ramtaskman.collector.psutil.cpu_percent', return_value=0):
            collector.sample()
            collector.sample()
        self.assertEqual(backend.attempts, [1, 2, 3])

    def test_cli_budget_and_replay_conflict(self):
        from ramtaskman.cli import main
        with patch('sys.argv', ['ramtaskman', '--open', 'x.rtm.json', '--max-measurements', '1']), \
             patch('sys.stderr'), self.assertRaises(SystemExit) as error:
            main()
        self.assertEqual(error.exception.code, 2)
        with patch('sys.argv', ['ramtaskman', '--max-measurements', '0']), \
             patch('sys.stderr'), self.assertRaises(SystemExit) as error:
            main()
        self.assertEqual(error.exception.code, 2)

    def test_unbounded_remains_existing_read_process_contract(self):
        backend = Backend()
        backend.read_process = lambda p: backend.read_metrics(p, backend.read_identity(p))
        snap = self.sample(Collector(backend=backend))
        self.assertEqual(snap.applications[0].total('rss'), 15)
        self.assertIsNone(snap.measurement_attempted)
        self.assertEqual(snap.measurement_deferred, 0)

    def test_unbounded_skipped_identity_makes_all_groups_incomplete(self):
        backend = Backend()
        backend.bad_identity.add(2)
        backend.read_process = lambda p: backend.read_metrics(p, backend.read_identity(p))
        snap = self.sample(Collector(backend=backend))
        self.assertEqual(snap.skipped, 1)
        self.assertFalse(snap.enumeration_complete)
        self.assertIsNone(snap.applications[0].total('rss'))
        self.assertFalse(snap.applications[0].membership_complete)

    def test_rejects_invalid_budget_or_backend_without_split_methods(self):
        for value in (0, -1, True, 1.5):
            with self.subTest(value=value), self.assertRaises(ValueError):
                Collector(backend=Backend(), max_measurements=value)
        with self.assertRaises(ValueError):
            Collector(backend=object(), max_measurements=1)

    def test_cancellation_during_identity_marks_all_groups_incomplete(self):
        backend = Backend()
        collector = Collector(backend=backend, max_measurements=3)
        calls = iter([False, False, True] + [True] * 10)
        with patch('ramtaskman.collector.psutil.process_iter', return_value=[FakeProcess(i) for i in range(1, 6)]), \
             patch('ramtaskman.collector.psutil.cpu_percent', return_value=0):
            snap = collector.sample(cancelled=lambda: next(calls))
        self.assertFalse(snap.enumeration_complete)
        self.assertEqual(snap.measurement_attempted, 0)
        self.assertEqual(snap.measurement_deferred, 2)
        self.assertEqual(backend.attempts, [])
        self.assertIsNone(snap.applications[0].total('rss'))
        self.assertTrue(all('annullata' in row.reason for row in snap.processes))

    def test_cancellation_during_metrics_preserves_identities_without_stale_values(self):
        backend = Backend()
        collector = Collector(backend=backend, max_measurements=3)
        calls = iter([False] * 6 + [True] * 5)
        with patch('ramtaskman.collector.psutil.process_iter', return_value=[FakeProcess(i) for i in range(1, 6)]), \
             patch('ramtaskman.collector.psutil.cpu_percent', return_value=0):
            snap = collector.sample(cancelled=lambda: next(calls))
        self.assertTrue(snap.enumeration_complete)
        self.assertEqual(snap.measurement_attempted, 1)
        self.assertEqual(snap.measurement_deferred, 4)
        self.assertEqual(len(snap.processes), 5)
        self.assertIsNone(snap.processes[1].rss)
        self.assertIn('annullata', snap.processes[1].reason)

    def test_cancellation_unbounded_has_incomplete_enumeration(self):
        backend = Backend()
        backend.read_process = lambda p: backend.read_metrics(p, backend.read_identity(p))
        calls = iter([False, True])
        with patch('ramtaskman.collector.psutil.process_iter', return_value=[FakeProcess(i) for i in range(1, 6)]), \
             patch('ramtaskman.collector.psutil.cpu_percent', return_value=0):
            snap = Collector(backend=backend).sample(cancelled=lambda: next(calls))
        self.assertFalse(snap.enumeration_complete)
        self.assertEqual(len(snap.processes), 1)
        self.assertIsNone(snap.applications[0].total('rss'))


if __name__ == '__main__':
    unittest.main()
