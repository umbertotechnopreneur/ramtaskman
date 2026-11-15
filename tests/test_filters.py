import unittest

from ramtaskman.filters import RowFilter, owner_options
from test_memory import fixture


class FilterTests(unittest.TestCase):
    def test_query_is_literal_case_insensitive_and_searches_helpers(self):
        snap = fixture()
        group = snap.applications[0]
        self.assertTrue(RowFilter('BROWSER-WORKER').matches(group, {}))
        self.assertTrue(RowFilter('/DEMO/BROWSER').matches(group, {}))
        self.assertFalse(RowFilter('[browser]').matches(group, {}))
        self.assertEqual(group.total('pss'), 800 << 20)
        self.assertEqual(len(group.processes), 2)

    def test_pid_is_exact_and_does_not_match_memory_or_pid_prefix(self):
        group = fixture().applications[0]
        self.assertTrue(RowFilter('101').matches(group, {}))
        self.assertFalse(RowFilter('10').matches(group, {}))
        self.assertFalse(RowFilter('900').matches(group, {}))

    def test_owner_and_memory_and_query_are_combined(self):
        group = fixture().applications[0]
        self.assertTrue(RowFilter('browser', 'uid:1000', 'swap').matches(group, {}))
        self.assertFalse(RowFilter('browser', 'uid:0', 'swap').matches(group, {}))
        self.assertFalse(RowFilter('editor', 'uid:1000', 'swap').matches(group, {}))

    def test_swap_partial_group_matches_without_inventing_total(self):
        snap = fixture()
        snap.processes[1].swap = None
        group = snap.applications[0]
        self.assertTrue(RowFilter(memory='swap').matches(group, {}))
        self.assertIsNone(group.total('swap'))
        self.assertFalse(RowFilter(memory='swap').matches(snap.applications[2], {}))

    def test_partial_ignores_backend_unsupported_metrics(self):
        snap = fixture()
        row = snap.processes[0]
        row.pss = row.swap = row.swap_pss = None
        unsupported = dict.fromkeys(('pss', 'swap', 'swap_pss'), 'unsupported')
        self.assertFalse(RowFilter(memory='partial').matches(row, unsupported))
        row.uss = None
        self.assertTrue(RowFilter(memory='partial').matches(row, unsupported))

    def test_owner_options_include_windows_accounts_and_keep_unknown_separate(self):
        snap = fixture()
        snap.processes[0].uid = None
        snap.processes[0].user = 'DOMAIN\\Alice'
        snap.processes[1].uid = None
        options = dict((key, label) for label, key in owner_options(snap.processes))
        self.assertEqual(options['user:DOMAIN\\Alice'], 'DOMAIN\\Alice')
        self.assertNotIn(None, options)
        self.assertIn('uid:0', options)
