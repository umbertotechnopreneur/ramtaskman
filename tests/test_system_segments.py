import json
import tempfile
import unittest
from pathlib import Path

from ramtaskman.backends.linux import read_system
from ramtaskman.memory_segments import partition_meminfo
from ramtaskman.models import Snapshot, SystemMemory
from ramtaskman.report import to_dict

K = 1024


def meminfo_fields():
    return dict(MemTotal=1000*K, MemFree=200*K, MemAvailable=500*K,
                AnonPages=300*K, Cached=250*K, Shmem=50*K, Buffers=30*K,
                SReclaimable=40*K, SUnreclaim=60*K, Slab=100*K,
                Mapped=150*K, SwapTotal=2000*K, SwapFree=1800*K)


class SystemSegmentTests(unittest.TestCase):
    def test_partition_is_disjoint_and_reconciles_to_usable_total(self):
        fields = meminfo_fields()
        parts, reason = partition_meminfo(fields)
        self.assertIsNone(reason)
        self.assertEqual(list(parts), ['anon', 'file_cache', 'shmem', 'buffers',
                                     'slab_reclaimable', 'slab_unreclaimable', 'other', 'free'])
        self.assertEqual(sum(parts.values()), fields['MemTotal'])
        self.assertEqual(parts['other'], 120*K)
        self.assertEqual(parts['anon'], 300*K)
        self.assertEqual(parts['free'], 200*K)

    def test_shmem_is_subtracted_from_file_cache_and_counted_once(self):
        fields = meminfo_fields()
        parts, _ = partition_meminfo(fields)
        self.assertEqual(parts['file_cache'], 200*K)
        self.assertEqual(parts['file_cache'] + parts['shmem'], fields['Cached'])

    def test_overlapping_metrics_are_not_added_as_parts(self):
        fields = meminfo_fields()
        original, _ = partition_meminfo(fields)
        fields.update(MemAvailable=950*K, Slab=999*K, Mapped=888*K,
                      Active=900*K, Pss=444*K, SwapTotal=9999*K)
        parts, _ = partition_meminfo(fields)
        self.assertEqual(parts, original)
        self.assertNotIn('available', parts)
        self.assertNotIn('slab', parts)
        self.assertNotIn('mapped', parts)

    def test_missing_counter_does_not_become_zero_or_partial_partition(self):
        fields = meminfo_fields()
        del fields['SUnreclaim']
        parts, reason = partition_meminfo(fields)
        self.assertEqual(parts, {})
        self.assertIn('SUnreclaim', reason)

    def test_inconsistent_samples_never_clip_or_normalize(self):
        for change in (dict(AnonPages=999*K), dict(Cached=10*K), dict(Shmem=-1), dict(MemTotal=0)):
            with self.subTest(change=change):
                fields = meminfo_fields()
                fields.update(change)
                parts, reason = partition_meminfo(fields)
                self.assertEqual(parts, {})
                self.assertTrue(reason)

    def test_measured_zero_segment_and_zero_residual_remain_zero(self):
        fields = meminfo_fields()
        fields.update(Shmem=0, MemTotal=880*K)
        parts, reason = partition_meminfo(fields)
        self.assertIsNone(reason)
        self.assertEqual(parts['shmem'], 0)
        self.assertEqual(parts['other'], 0)
        self.assertEqual(sum(parts.values()), fields['MemTotal'])

    def test_linux_backend_and_json_propagate_segments_and_reason(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fields = meminfo_fields()
            (root/'meminfo').write_text(''.join(f'{name}: {value//K} kB\n' for name, value in fields.items()))
            system = read_system(root)
            self.assertEqual(system.segments['file_cache'], 200*K)
            self.assertIsNone(system.segments_reason)
            result = json.loads(json.dumps(to_dict(Snapshot(1, system, []))))
            self.assertEqual(result['system']['segments'], system.segments)
            self.assertIsNone(result['system']['segments_reason'])
            del fields['AnonPages']
            (root/'meminfo').write_text(''.join(f'{name}: {value//K} kB\n' for name, value in fields.items()))
            system = read_system(root)
            self.assertEqual(system.segments, {})
            self.assertIn('AnonPages', system.segments_reason)

    def test_existing_cross_platform_constructors_keep_unknown_partition(self):
        system = SystemMemory(100, 60, 20, None, None, None, None)
        self.assertEqual(system.segments, {})
        self.assertIsNone(system.segments_reason)

    def test_linux_commit_and_missing_optional_fields_remain_distinct(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fields = meminfo_fields()
            fields.update(Committed_AS=0, CommitLimit=2000*K)
            def read():
                (root/'meminfo').write_text(''.join(f'{name}: {value//K} kB\n' for name, value in fields.items()))
                return read_system(root)
            system = read()
            data = to_dict(Snapshot(1, system, []))['system']
            self.assertEqual(data['linux_details'], {'commit_total': 0, 'commit_limit': 2000*K})
            del fields['Committed_AS'], fields['CommitLimit'], fields['Slab'], fields['Cached']
            system = read()
            self.assertIsNone(system.linux_details.commit_total)
            self.assertIsNone(system.linux_details.commit_limit)
            self.assertIsNone(system.cache)
            self.assertIsNone(system.slab)
            self.assertEqual(json.loads(json.dumps(to_dict(Snapshot(1, system, []))))['system']['linux_details']['commit_total'], None)
