"""Unit test module."""
import logging
import os
import sys
import unittest

import tools
from validation import uv_check  # noqa: E402

tests_dir = os.path.dirname(__file__)
addon_dir = os.path.dirname(tests_dir)

sys.path.insert(0, tests_dir)
sys.path.insert(0, addon_dir)


if __name__ == '__main__':
    # Load the addon module
    tools.LoadModule(os.path.join(addon_dir, '__init__.py'))

    # initialize the test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # add tests to the test suite
    suite.addTests(loader.loadTestsFromModule(uv_check))

    # initialize a runner, pass it your suite and run it
    runner = unittest.TextTestRunner(verbosity=0)
    runner.run(suite)

    logging.info('All tests have passed')
    # close blender process
    sys.exit()
