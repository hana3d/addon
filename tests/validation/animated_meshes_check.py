"""Animated mesh check tests."""
import unittest
from os.path import dirname, join

import bpy

from hana3d_dev.src.validators.animated_meshes_check import animated_meshes_check  # isort:skip


class AnimatedMeshesCheck(unittest.TestCase):  # noqa: D101
    def setUp(self):
        """Load test scene."""
        bpy.ops.wm.open_mainfile(
            filepath=join(dirname(__file__), '../scenes/animated_meshes_check.blend'),
        )

    def test_correct_model(self):
        """Test validation function on correct model."""
        export_data = {
            'models': ['Armature', 'Cube', 'Sphere'],
            'type': 'MODEL',
        }
        expected_result = (True, 'Asset has no animated meshes wrongly parented.')
        animated_meshes_check.run_validation(export_data)
        test_result = animated_meshes_check.get_validation_result()
        self.assertTrue(test_result == expected_result)

    def test_material(self):
        """Test validation function on correct material."""
        export_data = {
            'material': 'Material',
            'type': 'MATERIAL',
        }
        expected_result = (True, 'Asset has no animated meshes wrongly parented.')
        animated_meshes_check.run_validation(export_data)
        test_result = animated_meshes_check.get_validation_result()
        self.assertTrue(test_result == expected_result)

    def test_non_armature_object(self):
        """Test validation function on non armature object."""
        export_data = {
            'models': ['Torus'],
            'type': 'MODEL',
        }
        expected_result = (True, 'Asset has no animated meshes wrongly parented.')
        animated_meshes_check.run_validation(export_data)
        test_result = animated_meshes_check.get_validation_result()
        self.assertTrue(test_result == expected_result)

    def test_incorrect_model(self):
        """Test validation functions on incorrect model."""
        export_data = {
            'models': ['Armature.001', 'Icosphere', 'Cone'],
            'type': 'MODEL',
        }
        expected_result = (False, 'Static meshes parented to armature: Icosphere, Cone')
        animated_meshes_check.run_validation(export_data)
        test_result = animated_meshes_check.get_validation_result()
        self.assertTrue(test_result == expected_result)

    def test_incorrect_scene(self):
        """Test validation functions on incorrect scene."""
        export_data = {
            'scene': 'Scene',
            'type': 'SCENE',
        }
        expected_result = (False, 'Static meshes parented to armature: Icosphere, Cone')
        animated_meshes_check.run_validation(export_data)
        test_result = animated_meshes_check.get_validation_result()
        self.assertTrue(test_result == expected_result)
