import unittest
from dataclasses import FrozenInstanceError, replace

from ramtaskman.capture_models import freeze_snapshot, LINUX_METRIC_DEFINITIONS
from ramtaskman.comparison import compare_captures
from ramtaskman.regions import MemoryRegion, RegionSnapshot


def reg(start=0x1000, end=0x2000, **kwargs):
    return MemoryRegion(start, end, rss=kwargs.pop('rss', 100), pss=kwargs.pop('pss', 50),
                        uss=kwargs.pop('uss', 0), swap=kwargs.pop('swap', 0), **kwargs)


def cap(regions, *, sequence=1, complete=True, session='session', pid=42, started=1.,
        executable='/demo/app', definitions=None):
    snapshot = RegionSnapshot(pid, started, 'demo', 1700000000., regions, 5.,
                              None if complete else 'budget', complete)
    return freeze_snapshot(snapshot, collection_session_id=session, sequence=sequence,
                           executable_identity=executable, metric_definitions=definitions)


class ComparisonTests(unittest.TestCase):
    def test_immutable_baseline_copies_region_and_nested_data(self):
        region = reg(breakdown={'private_clean': 12}, vm_flags=('rd',))
        snap = RegionSnapshot(42, 1., 'demo', 1., [region])
        a = freeze_snapshot(snap, collection_session_id='session', sequence=1)
        region.rss = 999
        region.breakdown['private_clean'] = 999
        snap.regions.clear()
        self.assertEqual(a.regions[0].rss, 100)
        self.assertEqual(a.regions[0].breakdown['private_clean'], 12)
        with self.assertRaises(TypeError):
            a.regions[0].breakdown['private_clean'] = 33
        with self.assertRaises(FrozenInstanceError):
            a.regions[0].rss = 1
        with self.assertRaises(TypeError):
            a.metric_definitions['rss'] = 'incorrect'

    def test_matching_delta_null_zero_and_reverse_order(self):
        a = cap([reg(rss=100, uss=None)], sequence=8)
        b = cap([reg(rss=130, uss=0)], sequence=7)
        diff = compare_captures(a, b)
        self.assertTrue(diff.compatible)
        self.assertTrue(diff.reverse_order)
        self.assertEqual(diff.rows[0].status, 'same_interval')
        self.assertEqual(diff.rows[0].delta('rss'), 30)
        self.assertIsNone(diff.rows[0].delta('uss'))
        self.assertEqual(diff.rows[0].delta('swap'), 0)
        self.assertEqual(diff.totals['rss'], 30)
        self.assertIsNone(diff.totals['uss'])

    def test_only_regions_and_partial_coverage(self):
        a = cap([reg(0x1000, 0x2000), reg(0x3000, 0x4000)], sequence=1)
        b = cap([reg(0x1000, 0x2000), reg(0x5000, 0x6000)], sequence=2)
        d = compare_captures(a, b)
        self.assertEqual([r.status for r in d.rows], ['same_interval', 'only_a', 'only_b'])
        self.assertEqual(d.rows[1].delta('rss'), -100)
        self.assertEqual(d.rows[2].delta('rss'), 100)
        partial = compare_captures(a, replace(b, complete=False, reason='limit'))
        self.assertEqual(partial.rows[1].status, 'unobserved')
        self.assertIsNone(partial.rows[1].delta('rss'))
        self.assertEqual(partial.rows[2].status, 'only_b')
        self.assertIsNone(partial.totals['rss'])
        partial_a = compare_captures(replace(a, complete=False), b)
        self.assertEqual(partial_a.rows[2].status, 'unobserved')

    def test_splits_and_merges_do_not_distribute_resident_bytes(self):
        a = cap([reg(0, 0x4000, rss=100)])
        b = cap([reg(0, 0x2000, rss=20), reg(0x2000, 0x4000, rss=120)], sequence=2)
        result = compare_captures(a, b)
        self.assertEqual(len(result.rows), 1)
        self.assertEqual(result.rows[0].status, 'restructured')
        self.assertIsNone(result.rows[0].delta('rss'))
        self.assertEqual(result.totals['rss'], 40)
        self.assertEqual(compare_captures(b, a).rows[0].status, 'restructured')

    def test_backing_and_metadata_distinctions(self):
        a = cap([reg(inode=7, device='08:01', offset=0, path='/demo/a file')])
        b = cap([reg(inode=7, device='08:01', offset=0, path='/demo/a file (deleted)', permissions='r--p')], sequence=2)
        d = compare_captures(a, b)
        self.assertEqual(d.rows[0].status, 'metadata_changed')
        self.assertIn('path', d.rows[0].changes)
        self.assertEqual(d.rows[0].delta('rss'), 0)
        b = cap([reg(inode=9, device='08:01', path='/demo/a file')], sequence=2)
        d = compare_captures(a, b)
        self.assertEqual(d.rows[0].status, 'backing_changed')
        self.assertIsNone(d.rows[0].delta('rss'))
        unknown = cap([reg(path='/demo/no-inode')], sequence=2)
        unverified = compare_captures(unknown, unknown)
        self.assertEqual(unverified.rows[0].status, 'backing_unverified')
        self.assertIsNone(unverified.rows[0].delta('rss'))

    def test_incompatible_origin_process_platform_and_metric_semantics(self):
        a = cap([reg()])
        for b in (cap([reg()], session='other'), cap([reg()], pid=43),
                  cap([reg()], started=2.), cap([reg()], executable='/demo/new'),
                  cap([reg()], executable=None)):
            diff = compare_captures(a, b)
            self.assertFalse(diff.compatible)
            self.assertEqual(diff.rows, ())
            self.assertIsNone(diff.totals['rss'])
        self.assertFalse(compare_captures(cap([reg()], executable=None), cap([reg()], executable=None)).compatible)
        definitions = dict(LINUX_METRIC_DEFINITIONS, rss='native.different')
        b = cap([reg(rss=150)], sequence=2, definitions=definitions)
        diff = compare_captures(a, b)
        self.assertTrue(diff.compatible)
        self.assertIsNone(diff.rows[0].delta('rss'))
        self.assertIsNone(diff.totals['rss'])
        self.assertEqual(diff.rows[0].delta('pss'), 0)

    def test_invalid_intervals_and_empty_snapshots(self):
        a = cap([])
        b = cap([], sequence=2)
        self.assertEqual(compare_captures(a, b).totals['rss'], 0)
        self.assertIsNone(compare_captures(a, replace(b, complete=False)).totals['rss'])
        for rows in ([reg(2, 3), reg(1, 2)], [reg(1, 3), reg(2, 4)], [reg(3, 3)]):
            with self.assertRaises(ValueError):
                compare_captures(a, cap(rows))

    def test_adjacent_nonoverlapping_ranges_are_not_restructured(self):
        a = cap([reg(0, 10)])
        b = cap([reg(10, 20)], sequence=2)
        self.assertEqual([r.status for r in compare_captures(a,b).rows], ['only_a','only_b'])

    def test_transitive_overlap_forms_one_structure_without_splitting_values(self):
        a = cap([reg(0, 4), reg(4, 8), reg(8, 12)])
        b = cap([reg(0, 6), reg(6, 12)], sequence=2)
        result = compare_captures(a, b)
        self.assertEqual(len(result.rows), 1)
        self.assertEqual(result.rows[0].status, 'restructured')
        self.assertEqual((len(result.rows[0].before), len(result.rows[0].after)), (3, 2))
        self.assertIsNone(result.rows[0].delta('rss'))

    def test_special_and_anonymous_mappings_are_not_conflated(self):
        heap = cap([reg(path='[heap]', category='heap')])
        vdso = cap([reg(path='[vdso]', category='special')], sequence=2)
        result = compare_captures(heap, vdso).rows[0]
        self.assertEqual(result.status, 'backing_changed')
        self.assertIsNone(result.delta('rss'))
        vvar = cap([reg(path='[vvar]', category='special')], sequence=2)
        self.assertEqual(compare_captures(vdso, vvar).rows[0].status, 'backing_changed')
        anon = cap([reg(path='[anon:allocator]', category='anonymous')], sequence=2)
        self.assertEqual(compare_captures(heap, anon).rows[0].status, 'metadata_changed')


if __name__ == '__main__':
    unittest.main()
