import json
import io
import unittest

from rich.console import Console

from ramtaskman.detail import breakdown_total, detail_bars, detail_content
from ramtaskman.models import ApplicationMemory, ProcessMemory
from ramtaskman.report import to_dict
from test_memory import fixture


def complete_process(pid=7):
    return ProcessMemory(pid, 123.0, 'demo', 1000, '/demo/app',
                         pss=12 * 1024, rss=20 * 1024, uss=8 * 1024,
                         swap=16 * 1024, swap_pss=8 * 1024,
                         breakdown=dict(pss_anon=8 * 1024, pss_file=3 * 1024, pss_shmem=1024,
                                        private_clean=3 * 1024, private_dirty=5 * 1024,
                                        shared_clean=10 * 1024, shared_dirty=2 * 1024))


class DetailTests(unittest.TestCase):
    def test_separate_pss_and_rss_partitions_do_not_include_swap_or_duplicate_uss(self):
        proc = complete_process()
        bars = detail_bars(proc)
        self.assertEqual([bar.metric for bar in bars], ['PSS', 'RSS'])
        self.assertEqual([bar.total for bar in bars], [proc.pss, proc.rss])
        for bar in bars:
            self.assertTrue(bar.valid)
            self.assertEqual(sum(part.value for part in bar.parts), bar.total)
            self.assertFalse(any('Swap' in part.label or 'USS' in part.label for part in bar.parts))
        output = io.StringIO()
        Console(file=output, width=100, color_system=None).print(detail_content(proc, 'linux'))
        self.assertIn('Swap (fuori dalla RAM residente) 16.00 KiB', output.getvalue())

    def test_unknown_component_invalidates_only_its_own_dimension(self):
        proc = complete_process()
        del proc.breakdown['pss_file']
        pss, rss = detail_bars(proc)
        self.assertFalse(pss.valid)
        self.assertIn('0/1', pss.reason)
        self.assertEqual(pss.total, proc.pss)
        self.assertTrue(rss.valid)
        proc.rss = None
        self.assertFalse(detail_bars(proc)[1].valid)

    def test_group_requires_complete_readings_and_checks_each_member(self):
        first, second = complete_process(), complete_process(8)
        group = ApplicationMemory('demo', 'demo', 1000, '/demo/app', [first, second])
        self.assertEqual(detail_bars(group)[0].total, first.pss + second.pss)
        second.breakdown['pss_file'] = None
        self.assertIn('1/2', detail_bars(group)[0].reason)
        first, second = complete_process(), complete_process(8)
        first.rss += 4096
        second.rss -= 4096
        group.processes = [first, second]
        self.assertEqual(first.rss + second.rss, 40 * 1024)
        self.assertFalse(detail_bars(group)[1].valid)

    def test_pss_rounding_has_explicit_residual_never_rescaled_parts(self):
        proc = complete_process()
        proc.pss += 2048
        pss, rss = detail_bars(proc)
        self.assertTrue(pss.valid)
        self.assertEqual([part.value for part in pss.parts], [8192, 3072, 1024, 2048])
        self.assertIn('Arrotondamento', pss.parts[-1].label)
        self.assertIn('2.00 KiB', pss.note)
        self.assertEqual(sum(part.value for part in pss.parts), proc.pss)
        proc.pss += 1024
        self.assertFalse(detail_bars(proc)[0].valid)
        proc = complete_process()
        proc.pss -= 1024
        self.assertFalse(detail_bars(proc)[0].valid)
        proc = complete_process()
        proc.pss += 1
        self.assertFalse(detail_bars(proc)[0].valid)

    def test_zero_is_known_and_negative_values_are_not_rendered(self):
        proc = complete_process()
        proc.pss = proc.rss = proc.uss = 0
        proc.breakdown = dict.fromkeys(proc.breakdown, 0)
        for bar in detail_bars(proc):
            self.assertTrue(bar.valid)
            self.assertIn('0 B', bar.render(74).plain)
            self.assertNotIn('n/a', bar.render(74).plain)
            self.assertEqual(bar.render(74).cell_len, 74)
        proc.breakdown['pss_anon'] = -1024
        proc.breakdown['pss_file'] = 1024
        self.assertFalse(detail_bars(proc)[0].valid)

    def test_bars_fill_available_width_and_preserve_tiny_segments_in_legend(self):
        proc = complete_process()
        for bar in detail_bars(proc):
            for width in (1, 5, 20, 74, 154, 314):
                with self.subTest(metric=bar.metric, width=width):
                    output = io.StringIO()
                    Console(file=output, width=width, color_system=None).print(bar)
                    self.assertEqual(len(output.getvalue().rstrip('\n')), width)
                    self.assertEqual(bar.render(width).cell_len, width)
            self.assertGreater(len(bar.render(74).spans), 1)
        self.assertIn('Shmem 1.00 KiB', detail_bars(proc)[0].legend().plain)

    def test_group_detail_is_complete_or_unknown_never_partial_total(self):
        snap = fixture()
        snap.processes[0].breakdown = {'pss_anon': 100, 'pss_file': 0}
        snap.processes[1].breakdown = {'pss_anon': 40}
        group = snap.applications[0]
        self.assertEqual(breakdown_total(group, 'pss_anon'), (140, 2, 2))
        self.assertEqual(breakdown_total(group, 'pss_file'), (None, 1, 2))
        self.assertEqual(breakdown_total(group, 'pss_shmem'), (None, 0, 2))
        self.assertEqual(breakdown_total(snap.processes[0], 'pss_file'), (0, 1, 1))

    def test_grouping_provenance_and_granular_nulls_survive_json(self):
        snap = fixture()
        proc = snap.processes[0]
        proc.app_id = '/user.slice/user-1000.slice/user@1000.service/app.slice/app-demo-1.scope'
        proc.app_name = 'demo'
        proc.app_source = 'systemd-cgroup'
        proc.breakdown = {'pss_anon': 123, 'pss_file': None}
        result = json.loads(json.dumps(to_dict(snap)))
        self.assertEqual(result['applications'][0]['grouping'], 'cgroup')
        self.assertEqual(result['applications'][0]['grouping_id'], proc.app_id)
        self.assertEqual(result['processes'][0]['breakdown']['pss_anon'], 123)
        self.assertIsNone(result['processes'][0]['breakdown']['pss_file'])
