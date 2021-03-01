"""UV Check Validator."""
import logging
from contextlib import suppress
from typing import List, Tuple

import bpy

from . import BaseValidator, Category
from ..asset.asset_type import AssetType


def _get_rectangular_textures(models: List[str]) -> List[str]:
    textures = []
    for model in models:
        with suppress(AttributeError):
            for mat_slot in bpy.data.objects[model].material_slots:
                for node in mat_slot.material.node_tree.nodes:
                    if node.type == 'TEX_IMAGE':
                        if node.image.size[0] != node.image.size[1]:
                            textures.append(node.image.name)
    return textures


def _get_object_list(asset_type: AssetType, export_data: dict):
    if asset_type == AssetType.model:
        return export_data.get('models', [])
    elif asset_type == AssetType.scene:
        scene_name = export_data.get('scene')
        scene = bpy.data.scenes[scene_name]
        return scene.objects.keys()
    return []


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

    models = _get_object_list(asset_type, export_data)
    rectangular_textures = _get_rectangular_textures(models)
    if rectangular_textures:
        message = f'Rectangular textures: {", ".join(rectangular_textures)}'
        is_valid = False

    logging.info(message)
    return is_valid, message


name = 'Square Textures'
description = 'Checks for textures dimension'
square_textures = BaseValidator(name, Category.error, description, check_texture_dimension)
