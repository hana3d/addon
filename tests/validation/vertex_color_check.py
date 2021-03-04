"""Vertex color tests."""
import unittest
from os.path import dirname, join

import bpy

from hana3d_dev.src.validators.vertex_color_check import vertex_color_checker


class TestVertexColor(unittest.TestCase):  # noqa: D101
    def setUp(self):
        """Load test scene."""
        bpy.ops.wm.open_mainfile(filepath=join(dirname(__file__), '../scenes/vertex_color.blend'))

    def test_correct_model(self):
        """Test validation function on correct model."""
        export_data = {
            'models': ['Torus'],
            'type': 'MODEL',
        }
        expected_result = (True, 'All meshes have no vertex colors.')
        vertex_color_checker.run_validation(export_data)
        test_result = vertex_color_checker.get_validation_result()
        self.assertTrue(test_result == expected_result)

    def test_correct_material(self):
        """Test validation function on correct material."""
        export_data = {
            'material': 'Material',
            'type': 'MATERIAL',
        }
        expected_result = (True, 'All meshes have no vertex colors.')
        vertex_color_checker.run_validation(export_data)
        test_result = vertex_color_checker.get_validation_result()
        self.assertTrue(test_result == expected_result)

    def test_incorrect_model(self):
        """Test validation function on incorrect model."""
        export_data = {
            'models': ['Cube'],
            'type': 'MODEL',
        }
        expected_result = (False, 'Meshes with vertex colors: Cube')
        vertex_color_checker.run_validation(export_data)
        test_result = vertex_color_checker.get_validation_result()
        self.assertTrue(test_result == expected_result)

    def test_scene_and_fix(self):
        """Test validation function on incorrect scene and fix."""
        export_data = {
            'scene': 'Scene',
            'type': 'SCENE',
        }
        expected_result = (False, 'Meshes with vertex colors: Cube')
        vertex_color_checker.run_validation(export_data)
        test_result = vertex_color_checker.get_validation_result()
        self.assertTrue(test_result == expected_result)

        # Run fix
        expected_result = (True, 'All meshes have no vertex colors.')
        vertex_color_checker.run_fix(export_data)
        vertex_color_checker.run_validation(export_data)
        test_result = vertex_color_checker.get_validation_result()
        self.assertTrue(test_result == expected_result)
