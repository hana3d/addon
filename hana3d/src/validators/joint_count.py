"""Joint Count Validator."""

import logging
from typing import List, Tuple

import bpy

from . import BaseValidator, Category
from ..asset.asset_type import AssetType

MAX_JOINT_COUNT = 254


def _get_joint_count(object_names: List[str]) -> int:
    joint_count = 0
    for object_name in object_names:
        blend_object = bpy.data.objects[object_name]
        if blend_object.type == 'ARMATURE':
            joint_count += len(blend_object.data.bones)
    return joint_count


def _get_object_list(asset_type: AssetType, export_data: dict):
    if asset_type == AssetType.model:
        return export_data.get('models', [])
    if asset_type == AssetType.scene:
        scene_name = export_data.get('scene')
        scene = bpy.data.scenes[scene_name]
        return scene.objects.keys()
    return []


def check_joint_count(asset_type: AssetType, export_data: dict) -> Tuple[bool, str]:
    """Check if joint count is less than MAX_JOINT_COUNT.

    Parameters:
        asset_type: type of asset that will be uploaded
        export_data: dict containing objects to be uploaded info

    Returns:
        is_valid, message: if check passed and a report message
    """
    logging.info('Running joint count...')
    object_list = _get_object_list(asset_type, export_data)
    joint_count = _get_joint_count(object_list)
    message = f'Asset has {joint_count} bones'

    logging.info(message)
    return joint_count <= MAX_JOINT_COUNT, message


name = 'Joint Count'
description = f'Checks if number of bones <= {MAX_JOINT_COUNT}'
joint_count = BaseValidator(name, Category.error, description, check_joint_count)
