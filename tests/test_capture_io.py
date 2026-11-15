import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from ramtaskman.capture_io import CaptureFormatError, load_capture, save_capture
from ramtaskman.capture_models import freeze_snapshot
from ramtaskman.regions import MemoryRegion, RegionSnapshot


def fixture(sequence=1, capture_id='one'):
    region = MemoryRegion(0x1000, 0x2000, 'rw-p', 0, '00:00', 0, '/demo/uno spazio',
                          'file', rss=0, pss=None, uss=0, swap=0, swap_pss=0,
                          breakdown={'private_dirty': 0, 'anonymous': None}, vm_flags=('rd', 'wr'))
    snapshot = RegionSnapshot(100, 1700.25, 'esempio', time.time(), [region], 2.0,
                              reason=None, complete=True)
    return freeze_snapshot(snapshot, collection_session_id='sessione', sequence=sequence,
                           executable_identity='/demo/app', capture_id=capture_id)


class CaptureIOTests(unittest.TestCase):
    def test_roundtrip_single_and_pair_preserves_roles_nulls_and_unicode(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'spazio è.rtm.json'
            a, b = fixture(1, 'a'), fixture(2, 'b')
            save_capture(path, a)
            loaded = load_capture(path)
            self.assertEqual(loaded.current, a)
            self.assertIsNone(loaded.baseline)
            save_capture(path, b, a, overwrite=True)
            loaded = load_capture(path)
            self.assertEqual((loaded.current, loaded.baseline), (b, a))
            self.assertEqual(loaded.current.regions[0].rss, 0)
            self.assertIsNone(loaded.current.regions[0].pss)
            self.assertIn('0x1000', path.read_text())

    def test_partial_capture_remains_partial(self):
        from dataclasses import replace
        capture = replace(fixture(), complete=False, reason='limite', issues=('limite',))
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'a.rtm.json'
            save_capture(path, capture)
            loaded = load_capture(path).current
            self.assertFalse(loaded.complete)
            self.assertEqual(loaded.reason, 'limite')
            self.assertIsNone(loaded.total('rss'))

    def test_identical_baseline_is_rejected_without_changing_file(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'a.rtm.json'
            path.write_text('original')
            capture = fixture()
            with self.assertRaisesRegex(CaptureFormatError, 'coincidono'):
                save_capture(path, capture, capture, overwrite=True)
            self.assertEqual(path.read_text(), 'original')

    def test_existing_not_overwritten_and_failure_cleans_temp(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'existing.rtm.json'
            path.write_text('original')
            with self.assertRaises(FileExistsError):
                save_capture(path, fixture())
            self.assertEqual(path.read_text(), 'original')
            with patch('ramtaskman.capture_io.os.replace', side_effect=OSError('disco')):
                with self.assertRaises(OSError):
                    save_capture(path, fixture(), overwrite=True)
            self.assertEqual(path.read_text(), 'original')
            self.assertEqual([p.name for p in Path(td).iterdir()], ['existing.rtm.json'])

    def test_reject_corrupt_duplicate_values_and_unsafe_text(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'a.rtm.json'
            save_capture(path, fixture())
            obj = json.loads(path.read_text())
            corruptions = [
                lambda d: d.update(schema_version=2),
                lambda d: d['captures'][0]['regions'][0].update(rss=True),
                lambda d: d['captures'][0]['regions'][0].update(start='0x01000'),
                lambda d: d['captures'][0]['regions'][0].update(path='\x1b[31m'),
                lambda d: d['captures'][0].update(taken=999999999999999),
                lambda d: d.update(current_capture_id='non esiste'),
                lambda d: d['captures'][0]['metric_coverage'].update(rss=[0, 1]),
                lambda d: d['captures'][0]['regions'].append(d['captures'][0]['regions'][0].copy()),
            ]
            for change in corruptions:
                data = json.loads(json.dumps(obj))
                change(data)
                path.write_text(json.dumps(data))
                with self.subTest(data=data), self.assertRaises(CaptureFormatError):
                    load_capture(path)
            path.write_text('{"format":"a","format":"b"}')
            with self.assertRaises(CaptureFormatError):
                load_capture(path)
            path.write_text('{"x":NaN}')
            with self.assertRaises(CaptureFormatError):
                load_capture(path)
            path.write_text('{"\\u001b[31m":"x"}')
            with self.assertRaises(CaptureFormatError):
                load_capture(path)
            data = json.loads(json.dumps(obj))
            data['captures'][0]['name'] = '\ud800'
            path.write_text(json.dumps(data))
            with self.assertRaises(CaptureFormatError):
                load_capture(path)

    def test_file_limit_enforced_during_read(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'a.rtm.json'
            path.write_bytes(b'0123456789')
            with patch('ramtaskman.capture_io.MAX_BYTES', 4):
                with self.assertRaises(CaptureFormatError):
                    load_capture(path)

    def test_cli_replay_never_constructs_collector(self):
        import sys
        from ramtaskman import cli
        with tempfile.TemporaryDirectory() as td:
            a, b = Path(td)/'a.rtm.json', Path(td)/'b.rtm.json'
            save_capture(a, fixture(1, 'a'))
            save_capture(b, fixture(2, 'b'))
            with patch.object(sys, 'argv', ['ramtaskman', '--compare', str(a), str(b)]), \
                 patch.object(cli, 'Collector', side_effect=AssertionError('live')), \
                 patch('ramtaskman.replay.ReplayApp.run') as run:
                self.assertEqual(cli.main(), 0)
                run.assert_called_once()
            save_capture(b, fixture(2, 'b'), fixture(1, 'a'), overwrite=True)
            with patch.object(sys, 'argv', ['ramtaskman', '--compare', str(a), str(b)]), \
                 patch.object(cli, 'Collector', side_effect=AssertionError('live')):
                self.assertEqual(cli.main(), 1)


if __name__ == '__main__':
    unittest.main()
