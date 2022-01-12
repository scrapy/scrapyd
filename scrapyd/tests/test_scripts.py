import io
import pkgutil
import sys

from twisted.trial import unittest

from scrapyd.scripts.scrapyd_run import main

__version__ = pkgutil.get_data(__package__, '../VERSION').decode('ascii').strip()


class ScriptsTest(unittest.TestCase):

    def test_print_version(self):
        sys.argv.append('--version')
        capturedOutput = io.StringIO()
        sys.stdout = capturedOutput
        main()
        sys.stdout = sys.__stdout__
        self.assertEqual(capturedOutput.getvalue(), f"Scrapyd {__version__}\n")

    def test_print_v(self):
        sys.argv.append('-v')
        capturedOutput = io.StringIO()
        sys.stdout = capturedOutput
        main()
        sys.stdout = sys.__stdout__
        self.assertEqual(capturedOutput.getvalue(), f"Scrapyd {__version__}\n")

    def test_twisted_options(self):
        """
        Test that the twisted options are correctly parsed.
        """
        sys.argv.append('--help')
        capturedOutput = io.StringIO()
        sys.stdout = capturedOutput
        main()
        sys.stdout = sys.__stdout__
        self.assertIn('twistd', capturedOutput.getvalue())
