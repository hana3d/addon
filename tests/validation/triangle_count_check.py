"""Triangle count tests."""
import unittest
from os.path import dirname, join

import bpy

from hana3d_dev.src.validators.triangle_count import triangle_count


class TestTriangleCount(unittest.TestCase):  # noqa: D101
    def setUp(self):
        """Load test scene."""
        bpy.ops.wm.open_mainfile(filepath=join(dirname(__file__), '../scenes/triangle_count.blend'))

    def test_correct_model(self):
        """Test validation function on correct model."""
        export_data = {
            'models': ['Cube'],
            'type': 'MODEL',
        }
        expected_result = (True, 'Asset has 12 triangles')
        triangle_count.run_validation(export_data)
        test_result = triangle_count.get_validation_result()
        self.assertTrue(test_result == expected_result)

    def test_material(self):
        """Test validation function on correct material."""
        export_data = {
            'material': 'Material.001',
            'type': 'MATERIAL',
        }
        expected_result = (True, 'Asset has 0 triangles')
        triangle_count.run_validation(export_data)
        test_result = triangle_count.get_validation_result()
        self.assertTrue(test_result == expected_result)

    def test_correct_model_with_modifiers(self):
        """Test validation function on correct model with modifiers."""
        export_data = {
            'models': ['Cone'],
            'type': 'MODEL',
        }
        expected_result = (True, 'Asset has 3246 triangles')
        triangle_count.run_validation(export_data)
        test_result = triangle_count.get_validation_result()
        self.assertTrue(test_result == expected_result)

    def test_non_mesh_object(self):
        """Test validation function on non mesh object."""
        export_data = {
            'models': ['Light'],
            'type': 'MODEL',
        }
        expected_result = (True, 'Asset has 0 triangles')
        triangle_count.run_validation(export_data)
        test_result = triangle_count.get_validation_result()
        self.assertTrue(test_result == expected_result)

    def test_incorrect_model(self):
        """Test validation functions on model with rectangular texture."""
        export_data = {
            'models': ['Sphere'],
            'type': 'MODEL',
        }
        expected_result = (False, 'Asset has 261632 triangles')
        triangle_count.run_validation(export_data)
        test_result = triangle_count.get_validation_result()
        self.assertTrue(test_result == expected_result)

    def test_incorrect_scene(self):
        """Test validation functions on scene with rectangular texture."""
        export_data = {
            'scene': 'Scene',
            'type': 'SCENE',
        }
        expected_result = (False, 'Asset has 264890 triangles')
        triangle_count.run_validation(export_data)
        test_result = triangle_count.get_validation_result()
        self.assertTrue(test_result == expected_result)
