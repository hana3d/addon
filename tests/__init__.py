"""Unit test module."""
import os
import sys
import unittest

tests_dir = os.path.dirname(__file__)
addon_dir = os.path.dirname(tests_dir)

sys.path.insert(0, tests_dir)
sys.path.insert(0, addon_dir)

import tools  # noqa: E402 isort:skip

from validation import (  # noqa: E402 isort:skip
    uv_check,
    texture_size_check,
    texture_square_check,
)

if __name__ == '__main__':
    # Load the addon module
    tools.LoadModule(os.path.join(addon_dir, '__init__.py'))

    # initialize the test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # add tests to the test suite
    suite.addTests(loader.loadTestsFromModule(uv_check))
    suite.addTests(loader.loadTestsFromModule(texture_size_check))
    suite.addTests(loader.loadTestsFromModule(texture_square_check))

    # initialize a runner and run suite
    runner = unittest.TextTestRunner(verbosity=0)
    runner.run(suite)

    print('All tests have passed')  # noqa: WPS421

    # close blender process
    sys.exit()
