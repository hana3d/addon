"""Unit test module."""
import os
import sys
import unittest

tests_dir = os.path.dirname(__file__)
addon_dir = os.path.dirname(tests_dir)

sys.path.insert(0, tests_dir)
sys.path.insert(0, addon_dir)


from validation import (  # noqa: E402 isort:skip
    animated_meshes_check,
    animation_count,
    double_sided_check,
    joint_count,
    material_count,
    morph_target_check,
    object_count,
    scale_check,
    texture_size_check,
    texture_square_check,
    triangle_count_check,
    uv_check,
    vertex_color_check,
)

if __name__ == '__main__':
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # add tests to the test suite
    suite.addTests(loader.loadTestsFromModule(animated_meshes_check))
    suite.addTests(loader.loadTestsFromModule(animation_count))
    suite.addTests(loader.loadTestsFromModule(double_sided_check))
    suite.addTests(loader.loadTestsFromModule(joint_count))
    suite.addTests(loader.loadTestsFromModule(material_count))
    suite.addTests(loader.loadTestsFromModule(morph_target_check))
    suite.addTests(loader.loadTestsFromModule(object_count))
    suite.addTests(loader.loadTestsFromModule(scale_check))
    suite.addTests(loader.loadTestsFromModule(texture_size_check))
    suite.addTests(loader.loadTestsFromModule(texture_square_check))
    suite.addTests(loader.loadTestsFromModule(triangle_count_check))
    suite.addTests(loader.loadTestsFromModule(uv_check))
    suite.addTests(loader.loadTestsFromModule(vertex_color_check))

    # run suite
    runner = unittest.TextTestRunner(verbosity=0)
    test_result = runner.run(suite)

    # ensure a non zero exit code
    if not test_result.wasSuccessful():
        exit(1)  # noqa: WPS421
