"""UV Check Validator."""
from contextlib import suppress
import logging
from typing import List, Tuple
import math

import bpy

from . import BaseValidator, Category
from ..asset.asset_type import AssetType


MAX_TEXTURE_SIZE = 2048


def _get_large_textures(models: List[str]) -> List[str]:
    textures = []
    for model in models:
        with suppress(AttributeError):
            for mat_slot in model.material_slots:
                for node in mat_slot.material.node_tree.nodes:
                    if node.type == 'TEX_IMAGE':
                        size = node.image.size[0]
                        if size > MAX_TEXTURE_SIZE or not ((size & (size - 1) == 0) and size != 0):
                            textures.append(node.image)
    return textures


def _get_object_list(asset_type: AssetType, export_data: dict):
    if asset_type == AssetType.model:
        return export_data.get('models', [])
    elif asset_type == AssetType.scene:
        scene_name = export_data.get('scene')
        scene = bpy.data.scenes[scene_name]
        return scene.objects.keys()
    return []


def fix_textures_size(asset_type: AssetType, export_data: dict):
    """Remove all inactive UV layers from export data.

    Parameters:
        asset_type: type of asset that will be uploaded
        export_data: dict containing objects to be uploaded info

    """
    models = _get_object_list(asset_type, export_data)
    large_textures = _get_large_textures(models)
    for texture in large_textures:
        if texture.size[0] != texture.size[1]:
            continue
        new_size = min(2**int(math.log(texture.size[0], 2)), MAX_TEXTURE_SIZE)
        texture.scale(new_size, new_size)


def check_textures_size(asset_type: AssetType, export_data: dict) -> Tuple[bool, str]:
    """Check for duplicated UV layers in a single mesh on export data.

    Parameters:
        asset_type: type of asset that will be uploaded
        export_data: dict containing objects to be uploaded info

    Returns:
        is_valid, message: if check passed and a report message
    """
    logging.info('Running Texture Size Check...')
    is_valid = True
    message = 'All textures are below 2048x2048!'

    models = _get_object_list(asset_type, export_data)
    large_textures = _get_large_textures(models)
    if large_textures:
        message = f'Meshes with more than 1 UV Map: {", ".join(large_textures)}'
        is_valid = False

    logging.info(message)
    return is_valid, message


name = 'Textures Size'
description = 'Checks for textures size'
uv_checker = BaseValidator(name, Category.error, description,
                           check_textures_size, fix_textures_size)
