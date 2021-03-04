"""Material Count Validator."""

import logging
from contextlib import suppress
from typing import Tuple

import bpy

from . import BaseValidator, Category
from ..asset.asset_type import AssetType

MAX_MATERIAL_COUNT = 10


def _get_material_count(object_name: str) -> int:
    material_count = 0
    with suppress(AttributeError):
        blend_object = bpy.data.objects[object_name]
        for mat in blend_object.material_slots:
            if mat.material:
                material_count += 1
    return material_count


def _get_object_list(asset_type: AssetType, export_data: dict):
    if asset_type == AssetType.model:
        return export_data.get('models', [])
    elif asset_type == AssetType.scene:
        scene_name = export_data.get('scene')
        scene = bpy.data.scenes[scene_name]
        return scene.objects.keys()
    return []


def check_material_count(asset_type: AssetType, export_data: dict) -> Tuple[bool, str]:
    """Check if material count is less than MAX_MATERIAL_COUNT.

    Parameters:
        asset_type: type of asset that will be uploaded
        export_data: dict containing objects to be uploaded info

    Returns:
        is_valid, message: if check passed and a report message
    """
    logging.info('Running material count...')
    material_count = 0
    object_list = _get_object_list(asset_type, export_data)
    for object_name in object_list:
        material_count = material_count + _get_material_count(object_name)
    message = f'Asset has {material_count} materials'

    logging.info(message)
    return material_count <= MAX_MATERIAL_COUNT, message


name = 'Material Count'
description = f'Checks if number of materials <= {MAX_MATERIAL_COUNT}'
material_count = BaseValidator(name, Category.warning, description, check_material_count)
