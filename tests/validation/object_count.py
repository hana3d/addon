"""Animation count tests."""
import unittest
from os.path import dirname, join

import bpy

from hana3d_dev.src.validators.object_count import object_count


class TestObjectCount(unittest.TestCase):  # noqa: D101
    def setUp(self):
        """Load test scene."""
        bpy.ops.wm.open_mainfile(
            filepath=join(dirname(__file__), '../scenes/object_count.blend'),
        )

    def test_correct_model(self):
        """Test validation function on correct model."""
        export_data = {
            'models': ['Cube', 'Cube.001', 'Cube.002', 'Cube.003', 'Cube.004', 'Cube.005'],
            'type': 'MODEL',
        }
        expected_result = (True, 'Asset has 6 objects')
        object_count.run_validation(export_data)
        test_result = object_count.get_validation_result()
        self.assertTrue(test_result == expected_result)

    def test_material(self):
        """Test validation function on correct material."""
        export_data = {
            'material': 'Material',
            'type': 'MATERIAL',
        }
        expected_result = (True, 'Asset has 0 objects')
        object_count.run_validation(export_data)
        test_result = object_count.get_validation_result()
        self.assertTrue(test_result == expected_result)

    def test_non_mesh_object(self):
        """Test validation function on non mesh object."""
        export_data = {
            'models': ['Armature'],
            'type': 'MODEL',
        }
        expected_result = (True, 'Asset has 1 objects')
        object_count.run_validation(export_data)
        test_result = object_count.get_validation_result()
        self.assertTrue(test_result == expected_result)

    def test_incorrect_scene(self):
        """Test validation functions on incorrect scene."""
        export_data = {
            'scene': 'Scene',
            'type': 'SCENE',
        }
        expected_result = (False, 'Asset has 313 objects')
        object_count.run_validation(export_data)
        test_result = object_count.get_validation_result()
        self.assertTrue(test_result == expected_result)
