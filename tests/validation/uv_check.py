"""UV Check tests."""
import unittest
from os.path import dirname, join

import bpy

from hana3d_dev.src.validators.uv_check import uv_checker


class TestUVCheck(unittest.TestCase):  # noqa: D101
    def setUp(self):
        """Load test scene."""
        bpy.ops.wm.open_mainfile(filepath=join(dirname(__file__), '../scenes/uv_check.blend'))

    def test_correct_model(self):
        """Test validation function on correct model."""
        export_data = {
            'models': ['Cube'],
            'type': 'MODEL',
        }
        expected_result = (True, 'No duplicated UVs detected!')
        uv_checker.run_validation(export_data)
        test_result = uv_checker.get_validation_result()
        self.assertTrue(test_result == expected_result)

    def test_material(self):
        """Test validation function on material."""
        export_data = {
            'material': 'Material.002',
            'type': 'MATERIAL',
        }
        expected_result = (True, 'No duplicated UVs detected!')
        uv_checker.run_validation(export_data)
        test_result = uv_checker.get_validation_result()
        self.assertTrue(test_result == expected_result)

    def test_incorrect_model(self):
        """Test validation function on incorrect model."""
        export_data = {
            'models': ['Thing', 'Armature', 'Torus'],
            'type': 'MODEL',
        }
        expected_result = (False, 'Meshes with more than 1 UV Map: Torus')
        uv_checker.run_validation(export_data)
        test_result = uv_checker.get_validation_result()
        self.assertTrue(test_result == expected_result)

    def test_scene_and_fix(self):
        """Test validation function on incorrect scene and fix."""
        export_data = {
            'scene': 'Scene',
            'type': 'SCENE',
        }
        expected_result = (False, 'Meshes with more than 1 UV Map: Torus')
        uv_checker.run_validation(export_data)
        test_result = uv_checker.get_validation_result()
        self.assertTrue(test_result == expected_result)

        # Run fix
        expected_result = (True, 'No duplicated UVs detected!')
        uv_checker.run_fix()
        uv_checker.run_validation(export_data)
        test_result = uv_checker.get_validation_result()
        self.assertTrue(test_result == expected_result)
