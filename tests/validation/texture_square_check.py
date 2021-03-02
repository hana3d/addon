"""UV Check tests."""
import unittest
from os.path import dirname, join

import bpy

from hana3d_dev.src.validators.square_textures import square_textures


class TestTextureSquare(unittest.TestCase):  # noqa: D101
    def setUp(self):
        """Load test scene."""
        bpy.ops.wm.open_mainfile(filepath=join(dirname(__file__), '../scenes/texture_check.blend'))

    def test_correct_model(self):
        """Test validation function on correct model."""
        export_data = {
            'models': ['Cube'],
            'type': 'MODEL',
        }
        expected_result = (True, 'All textures are square!')
        square_textures.run_validation(export_data)
        test_result = square_textures.get_validation_result()
        self.assertTrue(test_result == expected_result)

    def test_correct_material(self):
        """Test validation functions on correct material."""
        export_data = {
            'material': 'Material',
            'type': 'MATERIAL',
        }
        # Correct size
        expected_result = (True, 'All textures are square!')
        square_textures.run_validation(export_data)
        test_result = square_textures.get_validation_result()
        self.assertTrue(test_result == expected_result)

    def test_incorrect_model(self):
        """Test validation functions on model with incorrect texture size."""
        export_data = {
            'models': ['Sphere'],
            'type': 'MODEL',
        }
        expected_result = (False, 'Rectangular textures: TexturesCom_Grass0197_3_M.jpg')
        square_textures.run_validation(export_data)
        test_result = square_textures.get_validation_result()
        self.assertTrue(test_result == expected_result)

    def test_incorrect_material(self):
        """Test validation functions on model with incorrect texture size."""
        export_data = {
            'material': 'Material.001',
            'type': 'MATERIAL',
        }
        expected_result = (False, 'Rectangular textures: TexturesCom_Grass0197_3_M.jpg')
        square_textures.run_validation(export_data)
        test_result = square_textures.get_validation_result()
        self.assertTrue(test_result == expected_result)

    def test_incorrect_scene(self):
        """Test validation functions on scene with incorrect texture size."""
        export_data = {
            'scene': 'Scene',
            'type': 'SCENE',
        }
        expected_result = (
            False,
            'Rectangular textures: TexturesCom_Grass0197_3_M.jpg',
        )
        square_textures.run_validation(export_data)
        test_result = square_textures.get_validation_result()
        self.assertTrue(test_result == expected_result)
