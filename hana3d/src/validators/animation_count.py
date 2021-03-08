"""Animation Count Validator."""

import logging
from typing import List, Tuple

import bpy

from . import BaseValidator, Category
from ..asset.asset_type import AssetType

MAX_ANIMATION_COUNT = 1


def _get_animation_count(object_names: List[str]) -> int:
    animation_count = 0
    objects_seen = set()
    for object_name in object_names:
        blend_object = bpy.data.objects[object_name]
        if (  # noqa: WPS337
            blend_object.animation_data
            and blend_object.animation_data.action
            and blend_object.data not in objects_seen
        ):
            objects_seen.add(blend_object.data)
            animation_count += 1
    return animation_count


def _get_object_list(asset_type: AssetType, export_data: dict):
    if asset_type == AssetType.model:
        return export_data.get('models', [])
    if asset_type == AssetType.scene:
        scene_name = export_data.get('scene')
        scene = bpy.data.scenes[scene_name]
        return scene.objects.keys()
    return []


def check_animation_count(asset_type: AssetType, export_data: dict) -> Tuple[bool, str]:
    """Check if animation count is less than MAX_ANIMATION_COUNT.

    Parameters:
        asset_type: type of asset that will be uploaded
        export_data: dict containing objects to be uploaded info

    Returns:
        is_valid, message: if check passed and a report message
    """
    logging.info('Running animation count...')
    object_list = _get_object_list(asset_type, export_data)
    animation_count = _get_animation_count(object_list)
    message = f'Asset has {animation_count} animations'

    logging.info(message)
    return animation_count <= MAX_ANIMATION_COUNT, message


name = 'Animation Count'
description = f'Checks if number of animations <= {MAX_ANIMATION_COUNT}'
animation_count = BaseValidator(name, Category.error, description, check_animation_count)
