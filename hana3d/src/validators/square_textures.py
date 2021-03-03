"""UV Check Validator."""
import logging
from contextlib import suppress
from typing import List, Tuple

import bpy

from . import BaseValidator, Category
from ..asset.asset_type import AssetType


def _check_rectangular_image(image: bpy.types.Image) -> bool:
    return image.size[0] != image.size[1]


def _get_rectangular_textures_in_objects(models: List[str]) -> List[str]:
    textures = []
    with suppress(AttributeError):
        for model in models:
            for mat_slot in bpy.data.objects[model].material_slots:
                textures += _get_rectangular_textures_in_material(mat_slot.material)
    return textures


def _get_rectangular_textures_in_material(material: bpy.types.Material) -> List[str]:
    textures = []
    for node in material.node_tree.nodes:
        if node.type == 'TEX_IMAGE' and _check_rectangular_image(node.image):
            textures.append(node.image.name)    # noqa: WPS220
    return textures


def _get_incorrect_texture_names(asset_type: AssetType, export_data: dict):
    if asset_type == AssetType.model:
        return _get_rectangular_textures_in_objects(export_data.get('models', []))
    if asset_type == AssetType.scene:
        scene_name = export_data.get('scene')
        scene = bpy.data.scenes[scene_name]
        return _get_rectangular_textures_in_objects(scene.objects.keys())
    if asset_type == AssetType.material:
        material = bpy.data.materials[export_data.get('material')]
        return _get_rectangular_textures_in_material(material)


def check_texture_dimension(asset_type: AssetType, export_data: dict) -> Tuple[bool, str]:
    """Check if textures are square.

    Parameters:
        asset_type: type of asset that will be uploaded
        export_data: dict containing objects to be uploaded info

    Returns:
        is_valid, message: if check passed and a report message
    """
    logging.info('Running Square Texture Check...')
    is_valid = True
    message = 'All textures are square!'

    rectangular_textures = _get_incorrect_texture_names(asset_type, export_data)
    if rectangular_textures:
        message = f'Rectangular textures: {", ".join(rectangular_textures)}'
        is_valid = False

    logging.info(message)
    return is_valid, message


name = 'Square Textures'
description = 'Checks for textures dimension'
square_textures = BaseValidator(name, Category.error, description, check_texture_dimension)
