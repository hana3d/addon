"""Scale Validator."""

import logging
from typing import List, Tuple

import bpy
from mathutils import Vector

from . import BaseValidator, Category
from ..asset.asset_type import AssetType

CORRECT_SCALE = Vector([1, 1, 1])


def _get_wrongly_scaled_objects(models: List[str]) -> List[str]:
    wrong_objects = []
    for model in models:
        blend_object = bpy.data.objects[model]
        if blend_object.scale != CORRECT_SCALE:
            wrong_objects.append(model)
    return wrong_objects


def _get_object_list(asset_type: AssetType, export_data: dict):
    if asset_type == AssetType.model:
        return export_data.get('models', [])
    if asset_type == AssetType.scene:
        scene_name = export_data.get('scene')
        scene = bpy.data.scenes[scene_name]
        return scene.objects.keys()
    return []


def check_scale(asset_type: AssetType, export_data: dict) -> Tuple[bool, str]:
    """Check if objects have (1,1,1) scale.

    Parameters:
        asset_type: type of asset that will be uploaded
        export_data: dict containing objects to be uploaded info

    Returns:
        is_valid, message: if check passed and a report message
    """
    logging.info('Running scale check...')
    is_valid = True
    message = 'All assets have (1,1,1) scale.'

    object_list = _get_object_list(asset_type, export_data)
    incorrect_objects = _get_wrongly_scaled_objects(object_list)

    if incorrect_objects:
        message = f'Objects with wrong scale: {", ".join(incorrect_objects)}'
        is_valid = False

    logging.info(message)
    return is_valid, message


def fix_scale(asset_type: AssetType, export_data: dict):
    """Set all objects scale to (1,1,1).

    Parameters:
        asset_type: type of asset that will be uploaded
        export_data: dict containing objects to be uploaded info
    """
    logging.info('Fixing scale...')

    object_list = _get_object_list(asset_type, export_data)
    incorrect_objects = _get_wrongly_scaled_objects(object_list)

    for object_name in incorrect_objects:
        bpy.data.objects[object_name].scale = CORRECT_SCALE


name = 'Scale check'
description = 'Checks if objects have (1,1,1) scale'
scale_check = BaseValidator(name, Category.warning, description, check_scale, fix_scale)
