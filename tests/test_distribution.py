import unittest

from tools.verify_distribution import REQUIRED, _check_names


class DistributionChecks(unittest.TestCase):
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
