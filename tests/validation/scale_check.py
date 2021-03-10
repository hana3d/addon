"""Scale check tests."""
import unittest
from os.path import dirname, join

import bpy

from hana3d_dev.src.validators.scale_check import scale_check


class TestObjectCount(unittest.TestCase):  # noqa: D101
    def setUp(self):
        """Load test scene."""
        bpy.ops.wm.open_mainfile(
            filepath=join(dirname(__file__), '../scenes/scale_check.blend'),
        )

    def test_correct_model(self):
        """Test validation function on correct model."""
        export_data = {
            'models': ['Cube'],
            'type': 'MODEL',
        }
        expected_result = (True, 'All objects have (1,1,1) scale.')
        scale_check.run_validation(export_data)
        test_result = scale_check.get_validation_result()
        self.assertTrue(test_result == expected_result)

    def test_material(self):
        """Test validation function on correct material."""
        export_data = {
            'material': 'Material',
            'type': 'MATERIAL',
        }
        expected_result = (True, 'All objects have (1,1,1) scale.')
        scale_check.run_validation(export_data)
        test_result = scale_check.get_validation_result()
        self.assertTrue(test_result == expected_result)

    def test_non_mesh_object(self):
        """Test validation function on non mesh object."""
        export_data = {
            'models': ['Armature'],
            'type': 'MODEL',
        }
        expected_result = (True, 'All objects have (1,1,1) scale.')
        scale_check.run_validation(export_data)
        test_result = scale_check.get_validation_result()
        self.assertTrue(test_result == expected_result)

    def test_incorrect_model(self):
        """Test validation functions on incorrect model."""
        export_data = {
            'models': ['Cone'],
            'type': 'MODEL',
        }
        expected_result = (False, 'Objects with wrong scale: Cone')
        scale_check.run_validation(export_data)
        test_result = scale_check.get_validation_result()
        self.assertTrue(test_result == expected_result)

    def test_and_fix_incorrect_scene(self):
        """Test validation functions on incorrect scene."""
        export_data = {
            'scene': 'Scene',
            'type': 'SCENE',
        }
        expected_result = (False, 'Objects with wrong scale: Cone')
        scale_check.run_validation(export_data)
        test_result = scale_check.get_validation_result()
        self.assertTrue(test_result == expected_result)

        # Run fix
        expected_result = (True, 'All objects have (1,1,1) scale.')
        scale_check.run_fix(export_data)
        test_result = scale_check.get_validation_result()
        self.assertTrue(test_result == expected_result)
