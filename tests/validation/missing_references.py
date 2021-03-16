"""Missing references tests."""
import unittest
from os.path import dirname, join

import bpy

from hana3d_dev.src.validators.missing_references import missing_references_check  # isort:skip


class TestMissingReferences(unittest.TestCase):  # noqa: D101
    def setUp(self):
        """Load test scene."""
        bpy.ops.wm.open_mainfile(
            filepath=join(dirname(__file__), '../scenes/missing_references.blend'),
        )

    def test_correct_model(self):
        """Test validation function on correct model."""
        export_data = {
            'models': ['Cube'],
            'type': 'MODEL',
        }
        expected_result = (True, 'All referenced textures exist!')
        missing_references_check.run_validation(export_data)
        test_result = missing_references_check.get_validation_result()
        self.assertTrue(test_result == expected_result)

    def test_correct_material(self):
        """Test validation functions on correct material."""
        export_data = {
            'material': 'Material',
            'type': 'MATERIAL',
        }
        expected_result = (True, 'All referenced textures exist!')
        missing_references_check.run_validation(export_data)
        test_result = missing_references_check.get_validation_result()
        self.assertTrue(test_result == expected_result)

    def test_incorrect_model(self):
        """Test validation functions on incorrect model."""
        export_data = {
            'models': ['Sphere'],
            'type': 'MODEL',
        }
        expected_result = (False, 'Textures missing: white-background-logo.png')
        missing_references_check.run_validation(export_data)
        test_result = missing_references_check.get_validation_result()
        self.assertTrue(test_result == expected_result)

    def test_incorrect_material(self):
        """Test validation functions on incorrect material."""
        export_data = {
            'material': 'Material.001',
            'type': 'MATERIAL',
        }
        expected_result = (False, 'Textures missing: white-background-logo.png')
        missing_references_check.run_validation(export_data)
        test_result = missing_references_check.get_validation_result()
        self.assertTrue(test_result == expected_result)

    def test_and_fix_incorrect_scene(self):
        """Test validation functions on scene with incorrect texture size."""
        export_data = {
            'scene': 'Scene',
            'type': 'SCENE',
        }
        expected_result = (False, 'Textures missing: white-background-logo.png')
        missing_references_check.run_validation(export_data)
        test_result = missing_references_check.get_validation_result()
        self.assertTrue(test_result == expected_result)

        # Run fix
        expected_result = (True, 'All referenced textures exist!')
        missing_references_check.run_fix(export_data)
        test_result = missing_references_check.get_validation_result()
        self.assertTrue(test_result == expected_result)
