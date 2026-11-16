import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from ramtaskman.backends.linux import LinuxBackend, parse_breakdown, read_app_cgroup
from ramtaskman.grouping import CGROUP_LIMIT, application_cgroup, unit_label
from ramtaskman.models import ProcessMemory
from test_memory import ROLLUP, fixture

PREFIX = '/user.slice/user-1000.slice/user@1000.service/app.slice/'


def cgroup(unit='app-org.example.Browser-42.scope', child=''):
    return f'0::{PREFIX}{unit}{child}\n'


def grouped_process(pid, executable, unit='app-org.example.Browser-42.scope', uid=1000):
    return ProcessMemory(pid, float(pid), 'helper', uid, executable, rss=100, pss=80, uss=50,
                         app_id=PREFIX + unit, app_name='org.example.Browser', app_source='systemd-cgroup')


class CgroupParsingTests(unittest.TestCase):
    def test_explicit_app_scope_including_delegated_children(self):
        expected = (PREFIX+'app-org.example.Browser-42.scope', 'org.example.Browser')
        self.assertEqual(application_cgroup(cgroup(), 1000), expected)
        self.assertEqual(application_cgroup(cgroup(child='/helpers/renderers'), 1000), expected)

    def test_systemd_escaping_and_known_launcher_label(self):
        unit = r'app-gnome-org.example.Editor\x2dnightly-987.scope'
        self.assertEqual(unit_label(unit), 'org.example.Editor-nightly')
        self.assertEqual(unit_label(r'app-gnome-caf\xc3\xa9-987.scope'), 'café')
        self.assertNotIn('\x1b', unit_label(r'app-gnome-bad\x1bname-987.scope'))
        identity = application_cgroup(cgroup(unit), 1000)
        self.assertEqual(identity[0], PREFIX+unit)

    def test_explicit_application_service_supported_generic_service_rejected(self):
        for unit, label in (
            ('app-gnome-org.example.Editor@123.service', 'org.example.Editor'),
            ('app-org.example.Editor.service', 'org.example.Editor'),
            ('app-flatpak-org.example.Editor@random.service', 'org.example.Editor'),
        ):
            self.assertEqual(application_cgroup(cgroup(unit), 1000), (PREFIX+unit, label))
        self.assertIsNone(application_cgroup(cgroup('dbus.service'), 1000))
        self.assertIsNone(application_cgroup(cgroup('terminal.scope'), 1000))

    def test_uid_mismatch_unknown_and_generic_session_are_not_evidence(self):
        for uid in (0, 1001, None):
            self.assertIsNone(application_cgroup(cgroup(), uid))
        for path in (
            '/user.slice/user-1000.slice/user@1000.service/app.slice',
            '/user.slice/user-1000.slice/session-1.scope',
            '/user.slice/user-1000.slice/user@1000.service/session.slice/app-foo-1.scope',
            '/system.slice/app-foo-1.scope',
            '/app.slice/app-foo-1.scope',
        ):
            self.assertIsNone(application_cgroup('0::'+path, 1000), path)

    def test_legacy_systemd_hierarchy_supported_but_cpu_memory_paths_ignored(self):
        path = PREFIX+'app-org.example.Browser-42.scope'
        self.assertEqual(application_cgroup('2:name=systemd:'+path,1000), (path,'org.example.Browser'))
        self.assertIsNone(application_cgroup('2:cpu,memory:'+path,1000))

    def test_ambiguous_hierarchies_and_nested_units_rejected(self):
        ambiguous = cgroup()+'2:name=systemd:'+PREFIX+'app-other-1.scope\n'
        self.assertIsNone(application_cgroup(ambiguous,1000))
        self.assertIsNone(application_cgroup(cgroup(child='/other.service'),1000))
        self.assertIsNone(application_cgroup(cgroup(child='/../other'),1000))

    def test_invalid_units_and_oversized_metadata_rejected(self):
        for unit in ('app-.scope', 'app-org.example.Browser.scope', 'app-org.example.Editor@.service',
                     'app-org.example.Editor@@123.service', r'app-bad\xZZ-1.scope', 'app-foo-1.slice'):
            self.assertIsNone(application_cgroup(cgroup(unit),1000),unit)
        self.assertIsNone(application_cgroup(cgroup()+'x'*CGROUP_LIMIT,1000))

    def test_bounded_file_read_and_permission_fallback(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'cgroup'
            path.write_text(cgroup()+'x'*CGROUP_LIMIT)
            self.assertIsNone(read_app_cgroup(path,1000))
            path.write_text(cgroup())
            self.assertIsNotNone(read_app_cgroup(path,1000))
        self.assertIsNone(read_app_cgroup(path,1000))
        with patch.object(Path,'open',side_effect=PermissionError):
            self.assertIsNone(read_app_cgroup(path,1000))


class ApplicationGroupingTests(unittest.TestCase):
    def test_helpers_with_different_executables_share_explicit_app_instance(self):
        snap=fixture()
        snap.processes=[grouped_process(1,'/demo/browser'),grouped_process(2,'/demo/renderer')]
        groups=snap.applications
        self.assertEqual(len(groups),1)
        self.assertEqual(groups[0].grouping,'cgroup')
        self.assertEqual(groups[0].name,'org.example.Browser')
        self.assertEqual(groups[0].total('pss'),160)
        self.assertIsNone(groups[0].executable)

    def test_separate_launches_and_users_never_combined(self):
        snap=fixture()
        snap.processes=[grouped_process(1,'/demo/browser'),
                        grouped_process(2,'/demo/browser','app-org.example.Browser-43.scope'),
                        grouped_process(3,'/demo/browser',uid=1001)]
        self.assertEqual(len(snap.applications),3)
        self.assertEqual(len({a.key for a in snap.applications}),3)

    def test_fallback_and_unknown_owner_not_absorbed_into_known_app(self):
        snap=fixture()
        a=grouped_process(1,'/demo/python')
        b=ProcessMemory(2,2,'python',1000,'/demo/python')
        c=grouped_process(3,'/demo/python',uid=None)
        d=grouped_process(4,'/demo/python',uid=None)
        snap.processes=[a,b,c,d]
        self.assertEqual(len(snap.applications),4)
        self.assertEqual(snap.applications[1].grouping,'executable')
        self.assertEqual(snap.applications[1].grouping_id,'/demo/python')

    def test_windows_does_not_treat_linux_app_fields_as_evidence(self):
        snap=fixture()
        snap.platform='windows'
        snap.processes=[grouped_process(1,'/demo/browser'),grouped_process(2,'/demo/renderer')]
        self.assertEqual(len(snap.applications),2)

    def test_incomplete_app_preserves_null_metrics(self):
        snap=fixture()
        snap.processes=[grouped_process(1,'/demo/browser'),grouped_process(2,'/demo/renderer')]
        snap.processes[1].pss=None
        self.assertIsNone(snap.applications[0].total('pss'))
        self.assertEqual(snap.applications[0].total('uss'),100)


class BreakdownTests(unittest.TestCase):
    def test_breakdown_missing_is_none_and_measured_zero_stays_zero(self):
        values=parse_breakdown(ROLLUP+'Pss_Anon: 60 kB\nPss_File: 10 kB\nPss_Shmem: 0 kB\n')
        self.assertEqual(values['pss_anon'],60*1024)
        self.assertEqual(values['pss_file'],10*1024)
        self.assertEqual(values['pss_shmem'],0)
        self.assertEqual(values['private_clean'],10*1024)
        self.assertEqual(values['shared_clean'],60*1024)
        self.assertIsNone(values['lazy_free'])
        self.assertIsNone(values['anon_huge_pages'])

    def test_backend_propagates_explicit_app_and_breakdown(self):
        process=Mock(pid=99)
        process.create_time.return_value=1
        process._proc.name.return_value='renderer'
        process.uids.return_value=Mock(real=1000)
        process._proc.exe.return_value='/demo/renderer'
        process.is_running.return_value=True
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            (root/'99').mkdir()
            (root/'99'/'cgroup').write_text(cgroup())
            (root/'99'/'smaps_rollup').write_text(ROLLUP+'Pss_Anon: 70 kB\n')
            row=LinuxBackend(root).read_process(process)
        self.assertEqual(row.app_id,PREFIX+'app-org.example.Browser-42.scope')
        self.assertEqual(row.app_source,'systemd-cgroup')
        self.assertEqual(row.breakdown['pss_anon'],70*1024)
        self.assertIsNone(row.breakdown['pss_file'])

    def test_backend_denied_rollup_does_not_invent_breakdown(self):
        process=Mock(pid=99)
        process.create_time.return_value=1
        process._proc.name.return_value='protected'
        process.uids.return_value=Mock(real=1000)
        process._proc.exe.return_value='/demo/protected'
        process.memory_info.return_value=Mock(rss=10)
        process.is_running.return_value=True
        with patch.object(Path,'read_text',side_effect=PermissionError), \
             patch.object(Path,'open',side_effect=PermissionError):
            row=LinuxBackend().read_process(process)
        self.assertEqual(row.breakdown,{})
        self.assertIsNone(row.app_id)
