import subprocess
import sys
import unittest


class CLITests(unittest.TestCase):
    def test_invalid_intervals_rejected_before_collecting(self):
        for value in ('0', '-1', 'nan', 'inf'):
            result = subprocess.run([sys.executable, '-m', 'ramtaskman', '--interval', value],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 2, value)

    def test_module_and_console_version_agree(self):
        from ramtaskman import __version__
        result = subprocess.run([sys.executable, '-m', 'ramtaskman', '--version'],
                                capture_output=True, text=True, check=True)
        self.assertEqual(result.stdout.strip(), __version__)
