"""Object count Validator."""

import logging
from typing import Tuple

import bpy

from . import BaseValidator, Category
from ..asset.asset_type import AssetType

MAX_OBJECT_COUNT = 300


def _get_object_list(asset_type: AssetType, export_data: dict):
    if asset_type == AssetType.model:
        return export_data.get('models', [])
    if asset_type == AssetType.scene:
        scene_name = export_data.get('scene')
        scene = bpy.data.scenes[scene_name]
        return scene.objects.keys()
    return []


def check_object_count(asset_type: AssetType, export_data: dict) -> Tuple[bool, str]:
    """Check if object count is less than MAX_OBJECT_COUNT.

    Parameters:
        asset_type: type of asset that will be uploaded
        export_data: dict containing objects to be uploaded info

    Returns:
        is_valid, message: if check passed and a report message
    """
    logging.info('Running object count...')
    object_list = _get_object_list(asset_type, export_data)
    object_count = len(object_list)
    message = f'Asset has {object_count} objects'
    is_valid = object_count <= MAX_OBJECT_COUNT

    if not is_valid:
        message = f'{message}. The AR may not work correctly on low memory iOS devices'

    logging.info(message)
    return is_valid, message


name = 'Object count'
description = f'Checks if asset has object count <= {MAX_OBJECT_COUNT}'
object_count = BaseValidator(name, Category.warning, description, check_object_count)
