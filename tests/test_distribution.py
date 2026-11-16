import unittest

from tools.verify_distribution import REQUIRED, _check_names, _verification_environment


class DistributionChecks(unittest.TestCase):
    def test_verification_reuses_caller_cache_and_isolates_imports(self):
        env = _verification_environment({'UV_CACHE_DIR': 'prepared-cache', 'PYTHONPATH': 'unwanted'})
        self.assertEqual(env['UV_CACHE_DIR'], 'prepared-cache')
        self.assertEqual(env['UV_PYTHON_DOWNLOADS'], 'never')
        self.assertNotIn('PYTHONPATH', env)
        self.assertTrue(_verification_environment({})['UV_CACHE_DIR'].endswith('.uv-cache'))

    def test_required_files_and_excluded_local_data(self):
        names = ['ramtaskman/' + name for name in REQUIRED] + ['ramtaskman-0.1.dist-info/licenses/LICENSE']
        _check_names(names, wheel=True)
        with self.assertRaisesRegex(ValueError, 'locale'):
            _check_names(names + ['ramtaskman/captures/real.svg'], wheel=True)
        with self.assertRaisesRegex(ValueError, 'locale'):
            _check_names(names + ['ramtaskman/.env.secret'], wheel=True)
        with self.assertRaisesRegex(ValueError, 'mancante'):
            _check_names(names[:-2] + names[-1:], wheel=True)


if __name__ == '__main__':
    unittest.main()
