import unittest

from tools.verify_distribution import REQUIRED, SOURCE_REQUIRED, _check_names, _verification_environment


class DistributionChecks(unittest.TestCase):
    def test_verification_reuses_caller_cache_and_isolates_imports(self):
        env = _verification_environment({'UV_CACHE_DIR': 'prepared-cache', 'PYTHONPATH': 'unwanted'})
        self.assertEqual(env['UV_CACHE_DIR'], 'prepared-cache')
        self.assertEqual(env['UV_PYTHON_DOWNLOADS'], 'never')
        self.assertNotIn('PYTHONPATH', env)
        self.assertTrue(_verification_environment({})['UV_CACHE_DIR'].endswith('.uv-cache'))

    def test_required_files_and_excluded_local_data(self):
        names = ['ramtaskman/' + name for name in REQUIRED] + [
            'ramtaskman-0.1.dist-info/licenses/LICENSE',
            'ramtaskman-0.1.dist-info/licenses/THIRD_PARTY_NOTICES.md',
        ]
        _check_names(names, wheel=True)
        with self.assertRaisesRegex(ValueError, 'locale'):
            _check_names(names + ['ramtaskman/captures/real.svg'], wheel=True)
        with self.assertRaisesRegex(ValueError, 'locale'):
            _check_names(names + ['ramtaskman/.env.secret'], wheel=True)
        for missing in (REQUIRED[-1], 'LICENSE', 'THIRD_PARTY_NOTICES.md'):
            with self.subTest(missing=missing), self.assertRaisesRegex(ValueError, 'mancante'):
                _check_names([name for name in names if not name.endswith('/' + missing)], wheel=True)

    def test_source_archive_preserves_docs_tools_and_lockfile(self):
        root = 'ramtaskman-0.1.0/'
        names = [root + 'src/ramtaskman/' + name for name in REQUIRED]
        names += [root + name for name in (*SOURCE_REQUIRED, 'LICENSE', 'THIRD_PARTY_NOTICES.md')]
        _check_names(names, wheel=False)
        for missing in SOURCE_REQUIRED:
            with self.subTest(missing=missing), self.assertRaisesRegex(ValueError, 'mancante'):
                _check_names([name for name in names if name != root + missing], wheel=False)


if __name__ == '__main__':
    unittest.main()
