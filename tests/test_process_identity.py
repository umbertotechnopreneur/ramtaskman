"""Native metadata must never expand into command lines or executable probes."""
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import psutil

from ramtaskman.backends.linux import LinuxBackend
from ramtaskman.backends.psutil_backend import PsutilBackend
from ramtaskman.backends.windows_regions import _verify as verify_windows
from ramtaskman.models import ProcessMemory
from ramtaskman.process_identity import process_executable, process_name
from ramtaskman.regions import LinuxRegionReader


def native_process():
    process = Mock(pid=17)
    process._proc = Mock(spec=['name', 'exe'])
    process._proc.name.return_value = 'long-native-process-name'
    process._proc.exe.return_value = '/demo/App'
    process.create_time.return_value = 42.0
    process.uids.return_value = SimpleNamespace(real=1000)
    process.username.return_value = 'demo-user'
    process.is_running.return_value = True
    for public in (process.name, process.exe, process.cmdline):
        public.side_effect = AssertionError('public metadata fallback is forbidden')
    return process


class NativeMetadataTests(unittest.TestCase):
    def test_long_name_and_executable_use_only_native_metadata(self):
        process = native_process()
        with patch('os.path.isfile', side_effect=AssertionError('executable probe')), \
             patch('os.access', side_effect=AssertionError('executable probe')):
            self.assertEqual(process_name(process), 'long-native-process-name')
            self.assertEqual(process_executable(process), '/demo/App')
        process.name.assert_not_called()
        process.exe.assert_not_called()
        process.cmdline.assert_not_called()

    def test_missing_native_adapter_never_uses_public_fallbacks(self):
        for native in (None, SimpleNamespace(), SimpleNamespace(name=None, exe=None)):
            with self.subTest(native=native):
                process = native_process()
                process._proc = native
                self.assertEqual(process_name(process), 'PID 17')
                self.assertIsNone(process_executable(process))
                process.name.assert_not_called()
                process.exe.assert_not_called()
                process.cmdline.assert_not_called()

        process = SimpleNamespace(pid=18)
        self.assertEqual(process_name(process), 'PID 18')
        self.assertIsNone(process_executable(process))

    def test_empty_or_invalid_native_values_are_unavailable(self):
        for value in ('', None, b'bytes', 0, object()):
            with self.subTest(value=value):
                process = native_process()
                process._proc.name.return_value = value
                process._proc.exe.return_value = value
                self.assertEqual(process_name(process), 'PID 17')
                self.assertIsNone(process_executable(process))

    def test_denied_or_changed_native_api_degrades_without_guessing(self):
        for error in (psutil.AccessDenied(17), PermissionError(),
                      AttributeError('native method absent'), NotImplementedError()):
            with self.subTest(error=type(error).__name__):
                process = native_process()
                process._proc.name.side_effect = error
                process._proc.exe.side_effect = error
                with patch('os.path.isfile', side_effect=AssertionError('executable probe')), \
                     patch('os.access', side_effect=AssertionError('executable probe')):
                    self.assertEqual(process_name(process), 'PID 17')
                    self.assertIsNone(process_executable(process))

    def test_disappeared_process_is_not_disguised_as_missing_metadata(self):
        for error in (psutil.NoSuchProcess(17), psutil.ZombieProcess(17), ProcessLookupError()):
            for read, field in ((process_name, 'name'), (process_executable, 'exe')):
                with self.subTest(error=type(error).__name__, field=field):
                    process = native_process()
                    getattr(process._proc, field).side_effect = error
                    with self.assertRaises(type(error)):
                        read(process)

    def test_public_caches_are_neither_reused_nor_rewritten(self):
        process = native_process()
        process._name = 'stale public name'
        process._exe = '/demo/stale'
        process._proc.name.side_effect = ['native first', 'native second']
        process._proc.exe.side_effect = ['/demo/first', '/demo/second']
        self.assertEqual([process_name(process), process_name(process)],
                         ['native first', 'native second'])
        self.assertEqual([process_executable(process), process_executable(process)],
                         ['/demo/first', '/demo/second'])
        self.assertEqual(process._name, 'stale public name')
        self.assertEqual(process._exe, '/demo/stale')


class IdentityIntegrationTests(unittest.TestCase):
    def test_all_backends_use_native_metadata_and_keep_identity_checks(self):
        for backend in (LinuxBackend(), PsutilBackend('windows'), PsutilBackend('macos')):
            with self.subTest(platform=backend.name):
                process = native_process()
                with patch('ramtaskman.backends.linux.read_app_cgroup', return_value=None):
                    row = backend.read_identity(process)
                self.assertEqual((row.pid, row.started_at, row.name),
                                 (17, 42.0, 'long-native-process-name'))
                self.assertEqual(row.executable, '\\demo\\app' if backend.name == 'windows' else '/demo/App')
                process.is_running.assert_called_once_with()
                process.is_running.return_value = False
                with patch('ramtaskman.backends.linux.read_app_cgroup', return_value=None):
                    self.assertIsNone(backend.read_identity(process))

    def test_backend_preserves_identity_when_native_metadata_is_denied(self):
        for backend in (LinuxBackend(), PsutilBackend('windows'), PsutilBackend('macos')):
            with self.subTest(platform=backend.name):
                process = native_process()
                process._proc.name.side_effect = psutil.AccessDenied(17)
                process._proc.exe.side_effect = psutil.AccessDenied(17)
                with patch('ramtaskman.backends.linux.read_app_cgroup', return_value=None):
                    row = backend.read_identity(process)
                self.assertEqual((row.pid, row.started_at, row.name, row.executable),
                                 (17, 42.0, 'PID 17', None))
                self.assertEqual(row.user if backend.name == 'windows' else row.uid,
                                 'demo-user' if backend.name == 'windows' else 1000)

    def test_region_identity_reads_native_executable_and_rejects_reused_pid(self):
        identity = ProcessMemory(17, 42.0, 'demo', 1000, '/demo/App')
        for verify, expected in ((LinuxRegionReader._verify_identity, '/demo/App'),
                                 (verify_windows, '\\demo\\app')):
            with self.subTest(verify=verify.__qualname__):
                process = native_process()
                with patch('psutil.Process', return_value=process):
                    self.assertEqual(verify(identity), expected)
                    process._proc.exe.side_effect = psutil.AccessDenied(17)
                    self.assertIsNone(verify(identity))
                    process.create_time.return_value = 43.0
                    with self.assertRaises(ProcessLookupError):
                        verify(identity)
                    process.create_time.return_value = 42.0
                    process.is_running.return_value = False
                    with self.assertRaises(ProcessLookupError):
                        verify(identity)
