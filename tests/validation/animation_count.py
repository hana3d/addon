"""Material count tests."""
import unittest
from os.path import dirname, join

import bpy

from hana3d_dev.src.validators.animation_count import animation_count


class TestAnimationCount(unittest.TestCase):  # noqa: D101
    def setUp(self):
        """Load test scene."""
        bpy.ops.wm.open_mainfile(filepath=join(dirname(__file__), '../scenes/animation_check.blend'))

    def test_correct_model(self):
        """Test validation function on correct model."""
        export_data = {
            'models': ['Icosphere'],
            'type': 'MODEL',
        }
        expected_result = (True, 'Asset has 1 animations')
        animation_count.run_validation(export_data)
        test_result = animation_count.get_validation_result()
        self.assertTrue(test_result == expected_result)

    def test_material(self):
        """Test validation function on correct material."""
        export_data = {
            'material': 'Material',
            'type': 'MATERIAL',
        }
        expected_result = (True, 'Asset has 0 animations')
        animation_count.run_validation(export_data)
        test_result = animation_count.get_validation_result()
        self.assertTrue(test_result == expected_result)

    def test_non_mesh_object(self):
        """Test validation function on non mesh object."""
        export_data = {
            'models': ['Armature'],
            'type': 'MODEL',
        }
        expected_result = (True, 'Asset has 1 animations')
        animation_count.run_validation(export_data)
        test_result = animation_count.get_validation_result()
        self.assertTrue(test_result == expected_result)

    def test_incorrect_model(self):
        """Test validation functions on incorrect model."""
        export_data = {
            'models': ['Cube', 'Cone'],
            'type': 'MODEL',
        }
        expected_result = (False, 'Asset has 2 animations')
        animation_count.run_validation(export_data)
        test_result = animation_count.get_validation_result()
        self.assertTrue(test_result == expected_result)

    def test_incorrect_scene(self):
        """Test validation functions on incorrect scene."""
        export_data = {
            'scene': 'Scene',
            'type': 'SCENE',
        }
        expected_result = (False, 'Asset has 4 animations')
        animation_count.run_validation(export_data)
        test_result = animation_count.get_validation_result()
        self.assertTrue(test_result == expected_result)
