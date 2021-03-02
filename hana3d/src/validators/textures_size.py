"""UV Check Validator."""
import logging
import math
from contextlib import suppress
from typing import List, Tuple

import bpy

from . import BaseValidator, Category
from ..asset.asset_type import AssetType

MAX_TEXTURE_SIZE = 2048


def _check_potency_of_two(number: int):
    return ((number & (number - 1) == 0) and number != 0)


def _check_node_for_wrong_texture(node: bpy.types.Node):
    if node.type == 'TEX_IMAGE':
        size = node.image.size[0]
        if size > MAX_TEXTURE_SIZE or not _check_potency_of_two(size):
            return True
    return False


def _get_large_textures(models: List[str]) -> List[str]:
    textures = []
    for model in models:
        with suppress(AttributeError):
            for mat_slot in bpy.data.objects[model].material_slots:
                for node in mat_slot.material.node_tree.nodes:
                    if _check_node_for_wrong_texture(node):
                        textures.append(node.image.name)    # noqa: WPS220
    return textures


def _get_incorrect_object_list(asset_type: AssetType, export_data: dict):
    if asset_type == AssetType.model:
        return _get_large_textures(export_data.get('models', []))
    elif asset_type == AssetType.scene:
        scene_name = export_data.get('scene')
        scene = bpy.data.scenes[scene_name]
        return _get_large_textures(scene.objects.keys())
    elif asset_type == AssetType.material:
        material = bpy.data.materials[export_data.get('material')]
        node = material.node_tree.nodes['Image Texture']
        if _check_node_for_wrong_texture(node):
            return [node.image.name]


def fix_textures_size(asset_type: AssetType, export_data: dict):
    """Resize textures to a potency of 2 below or equal to 2048.

    Parameters:
        asset_type: type of asset that will be uploaded
        export_data: dict containing objects to be uploaded info

    """
    large_textures = _get_incorrect_object_list(asset_type, export_data)
    for texture_name in large_textures:
        texture = bpy.data.images[texture_name]
        if texture.size[0] != texture.size[1]:
            continue
        new_size = min(2**int(math.log(texture.size[0], 2)), MAX_TEXTURE_SIZE)
        texture.scale(new_size, new_size)


def check_textures_size(asset_type: AssetType, export_data: dict) -> Tuple[bool, str]:
    """Check if textures sizes are potency of 2 and below or equal to 2048.

    Parameters:
        asset_type: type of asset that will be uploaded
        export_data: dict containing objects to be uploaded info

    Returns:
        is_valid, message: if check passed and a report message
    """
    logging.info('Running Texture Size Check...')
    is_valid = True
    message = 'All textures sizes are potency of 2 and below or equal to 2048!'

    large_textures = _get_incorrect_object_list(asset_type, export_data)
    if large_textures:
        message = f'Textures with wrong size: {", ".join(large_textures)}'
        is_valid = False

    logging.info(message)
    return is_valid, message


name = 'Textures Size'
description = 'Checks for textures size'
textures_size = BaseValidator(
    name,
    Category.error,
    description,
    check_textures_size,
    fix_textures_size,
)
