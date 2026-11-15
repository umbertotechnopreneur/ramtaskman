"""Portable wrapper checks; these do not replace native Mach/SDK verification."""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch


PROJECT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('verify_macos_regions', PROJECT / 'tools' / 'verify_macos_regions.py')
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


class ProbeWrapperTests(unittest.TestCase):
    def test_non_macos_does_not_compile_or_execute(self):
        with patch.object(probe.sys, 'platform', 'linux'), patch.object(probe.subprocess, 'run') as run, \
             contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(probe.main([]), 2)
        run.assert_not_called()

    def test_missing_compiler_fails_without_creating_scratch(self):
        with patch.object(probe.sys, 'platform', 'darwin'), patch.object(probe.shutil, 'which', return_value=None), \
             patch.object(probe.subprocess, 'run') as run, contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(probe.main([]), 2)
        run.assert_not_called()

    def test_build_and_run_uses_project_temp_and_cleans_it(self):
        scratch = PROJECT / 'captures'
        scratch.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='test-probe-', dir=scratch) as root:
            root = Path(root)
            calls = []

            def run(command, **kwargs):
                calls.append((command, kwargs))
                env = kwargs['env']
                self.assertTrue(Path(env['TMPDIR']).is_relative_to(root))
                self.assertTrue(Path(env['CLANG_MODULE_CACHE_PATH']).is_relative_to(root))
                if len(calls) == 1:
                    self.assertEqual(command[:4], ['/fake/cc', '-std=c11', '-D_DARWIN_C_SOURCE', '-O2'])
                    return subprocess.CompletedProcess(command, 0, '', '')
                data = {'probe': 'macos-self-region', 'page_bytes': 4096, 'munmap_ok': True}
                return subprocess.CompletedProcess(command, 0, json.dumps(data), '')

            out = io.StringIO()
            with patch.object(probe.sys, 'platform', 'darwin'), patch.object(probe, 'ROOT', root), \
                 patch.object(probe.shutil, 'which', return_value='/fake/cc'), \
                 patch.object(probe.subprocess, 'run', side_effect=run), contextlib.redirect_stdout(out):
                self.assertEqual(probe.main([]), 0)
            result = json.loads(out.getvalue())
            self.assertEqual(result['probe'], 'macos-self-region')
            self.assertEqual(result['probe_exit_code'], 0)
            self.assertEqual(len(calls), 2)
            self.assertEqual(list((root / 'captures').iterdir()), [])

    def test_build_and_probe_failures_are_explicit(self):
        scratch = PROJECT / 'captures'
        scratch.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='test-probe-', dir=scratch) as root:
            root = Path(root)
            fail = subprocess.CompletedProcess([], 1, '', 'SDK non disponibile')
            with patch.object(probe.sys, 'platform', 'darwin'), patch.object(probe, 'ROOT', root), \
                 patch.object(probe.shutil, 'which', return_value='/fake/cc'), \
                 patch.object(probe.subprocess, 'run', return_value=fail), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(probe.main([]), 2)
            self.assertEqual(list((root / 'captures').iterdir()), [])

    @unittest.skipUnless(shutil.which('cc') and probe.sys.platform.startswith('linux'),
                         'verifica di sintassi simulata richiede cc su Linux')
    def test_c_probe_walk_and_touch_with_simulated_headers(self):
        """Exercise C control flow with fake types: this is NOT a Darwin ABI check."""
        scratch = PROJECT / 'captures'
        scratch.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='test-probe-c-', dir=scratch) as directory:
            root = Path(directory)
            mach = root / 'mach'
            mach.mkdir()
            (mach / 'mach.h').write_text('''
#include <stdint.h>
typedef uint32_t natural_t, mach_msg_type_number_t;
typedef uint64_t mach_vm_address_t, mach_vm_size_t;
typedef int kern_return_t;
typedef int *vm_region_recurse_info_t;
#define KERN_SUCCESS 0
#define KERN_INVALID_ADDRESS 1
#define KERN_NO_SPACE 3
#define KERN_FAILURE 5
#define KERN_RESOURCE_SHORTAGE 6
#define KERN_NO_ACCESS 8
static inline uint32_t mach_task_self(void) { return 99; }
''')
            (mach / 'vm_region.h').write_text('''
typedef struct { int is_submap; unsigned pages_resident; } vm_region_submap_info_data_64_t;
#define VM_REGION_SUBMAP_INFO_COUNT_64 16
#define VM_REGION_SUBMAP_INFO_V0_COUNT_64 16
''')
            (mach / 'mach_vm.h').write_text('''
int mach_vm_region_recurse(uint32_t, mach_vm_address_t *, mach_vm_size_t *,
                           natural_t *, vm_region_recurse_info_t, mach_msg_type_number_t *);
''')
            fake = root / 'fake.c'
            fake.write_text('''
#include <mach/mach.h>
#include <mach/vm_region.h>
int mach_vm_region_recurse(uint32_t task, mach_vm_address_t *address, mach_vm_size_t *size,
                           natural_t *depth, vm_region_recurse_info_t output, mach_msg_type_number_t *count) {
    static unsigned touches;
    vm_region_submap_info_data_64_t *info = (vm_region_submap_info_data_64_t *)output;
    if (task != 99 || *count != 16) return KERN_FAILURE;
#ifdef SIMULATE_DENIAL
    return KERN_NO_ACCESS;
#endif
    if (*address >= 0x100000) {
        *size = 8u * 1024u * 1024u; info->is_submap = 0;
        info->pages_resident = touches++ ? 2048 : 0; return KERN_SUCCESS;
    }
    if (*address == 0 && *depth == 0) {
        *size = 0x2000; info->is_submap = 1; return KERN_SUCCESS;
    }
    if (*address == 0 && *depth == 1) {
        *address = 0x1000; *size = 0x1000; info->is_submap = 0; return KERN_SUCCESS;
    }
    return KERN_INVALID_ADDRESS;
}
''')
            binary = root / 'fake-probe'
            build = subprocess.run([shutil.which('cc'), '-std=c11', '-D__APPLE__', '-D_GNU_SOURCE',
                                    '-Wall', '-Wextra', '-Werror', '-I', str(root), str(probe.SOURCE),
                                    str(fake), '-o', str(binary)], capture_output=True, text=True, check=False)
            self.assertEqual(build.returncode, 0, build.stderr)
            result = subprocess.run([str(binary)], capture_output=True, text=True, check=False, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads(result.stdout)
            self.assertEqual(data['probe'], 'macos-self-region')
            self.assertEqual(data['before_resident_pages'], 0)
            self.assertEqual(data['after_resident_pages'], 2048)
            self.assertTrue(data['munmap_ok'])
            self.assertEqual(len(data['enumerations']), 3)
            self.assertTrue(all(walk['leaves'] == 1 and walk['submaps'] == 1 for walk in data['enumerations']))
            denied_binary = root / 'fake-denied'
            denied_build = subprocess.run([shutil.which('cc'), '-std=c11', '-D__APPLE__', '-D_GNU_SOURCE',
                                            '-DSIMULATE_DENIAL', '-Wall', '-Wextra', '-Werror', '-I', str(root),
                                            str(probe.SOURCE), str(fake), '-o', str(denied_binary)],
                                           capture_output=True, text=True, check=False)
            self.assertEqual(denied_build.returncode, 0, denied_build.stderr)
            denied = subprocess.run([str(denied_binary)], capture_output=True, text=True, check=False, timeout=10)
            self.assertEqual(denied.returncode, 1, denied.stderr)
            denied_data = json.loads(denied.stdout)
            self.assertEqual(denied_data['before_kr'], 8)
            self.assertIsNone(denied_data['before_resident_pages'])
            self.assertTrue(denied_data['munmap_ok'])


if __name__ == '__main__':
    unittest.main()
