"""Unit test module."""
import os
import sys
import unittest

tests_dir = os.path.dirname(__file__)
addon_dir = os.path.dirname(tests_dir)

sys.path.insert(0, tests_dir)
sys.path.insert(0, addon_dir)


from validation import (  # noqa: E402 isort:skip
    uv_check,
    texture_size_check,
    texture_square_check,
)

if __name__ == '__main__':
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # add tests to the test suite
    suite.addTests(loader.loadTestsFromModule(uv_check))
    suite.addTests(loader.loadTestsFromModule(texture_size_check))
    suite.addTests(loader.loadTestsFromModule(texture_square_check))

    # run suite
    runner = unittest.TextTestRunner(verbosity=0)
    test_result = runner.run(suite)

    # ensure a non zero exit code
    if not test_result.wasSuccessful():
        exit(1)  # noqa: WPS421
