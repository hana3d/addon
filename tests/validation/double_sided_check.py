"""Double sided tests."""
import unittest
from os.path import dirname, join

import bpy

from hana3d_dev.src.validators.double_sided import double_sided


class TestDoubleSided(unittest.TestCase):  # noqa: D101
    def setUp(self):
        """Load test scene."""
        bpy.ops.wm.open_mainfile(filepath=join(dirname(__file__), '../scenes/double_sided.blend'))

    def test_correct_model(self):
        """Test validation function on correct model."""
        export_data = {
            'models': ['Cube'],
            'type': 'MODEL',
        }
        expected_result = (True, 'All materials have backface culling enabled!')
        double_sided.run_validation(export_data)
        test_result = double_sided.get_validation_result()
        self.assertTrue(test_result == expected_result)

    def test_correct_material(self):
        """Test validation function on correct material."""
        export_data = {
            'material': 'Material',
            'type': 'MATERIAL',
        }
        expected_result = (True, 'All materials have backface culling enabled!')
        double_sided.run_validation(export_data)
        test_result = double_sided.get_validation_result()
        self.assertTrue(test_result == expected_result)

    def test_incorrect_model(self):
        """Test validation function on incorrect model."""
        export_data = {
            'models': ['Thing', 'Sphere'],
            'type': 'MODEL',
        }
        expected_result = (
            False,
            'Materials with backface culling disabled: Material.001, Material.002',
        )
        double_sided.run_validation(export_data)
        test_result = double_sided.get_validation_result()
        self.assertTrue(test_result == expected_result)

    def test_incorrect_material(self):
        """Test validation function on incorrect material."""
        export_data = {
            'material': 'Material.001',
            'type': 'MATERIAL',
        }
        expected_result = (
            False,
            'Materials with backface culling disabled: Material.001',
        )
        double_sided.run_validation(export_data)
        test_result = double_sided.get_validation_result()
        self.assertTrue(test_result == expected_result)

    def test_scene_and_fix(self):
        """Test validation function on incorrect scene and fix."""
        export_data = {
            'scene': 'Scene',
            'type': 'SCENE',
        }
        expected_result = (
            False,
            'Materials with backface culling disabled: Material.002, Material.001',
        )
        double_sided.run_validation(export_data)
        test_result = double_sided.get_validation_result()
        self.assertTrue(test_result == expected_result)

        # Run fix
        expected_result = (True, 'All materials have backface culling enabled!')
        double_sided.run_fix(export_data)
        double_sided.run_validation(export_data)
        test_result = double_sided.get_validation_result()
        self.assertTrue(test_result == expected_result)
