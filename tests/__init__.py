"""Unit test module."""
import os
import sys
import unittest

tests_dir = os.path.dirname(__file__)
addon_dir = os.path.dirname(tests_dir)

sys.path.insert(0, tests_dir)
sys.path.insert(0, addon_dir)


from validation import (  # noqa: E402 isort:skip
    double_sided_check,
    uv_check,
    texture_size_check,
    texture_square_check,
    triangle_count_check,
)

if __name__ == '__main__':
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # add tests to the test suite
    suite.addTests(loader.loadTestsFromModule(double_sided_check))
    suite.addTests(loader.loadTestsFromModule(uv_check))
    suite.addTests(loader.loadTestsFromModule(texture_size_check))
    suite.addTests(loader.loadTestsFromModule(texture_square_check))
    suite.addTests(loader.loadTestsFromModule(triangle_count_check))

    # run suite
    runner = unittest.TextTestRunner(verbosity=0)
    test_result = runner.run(suite)

    # ensure a non zero exit code
    if not test_result.wasSuccessful():
        exit(1)  # noqa: WPS421
