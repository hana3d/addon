"""Triangle count Validator."""

import logging
from contextlib import suppress
from typing import List, Tuple

import bpy

from . import BaseValidator, Category
from ..asset.asset_type import AssetType

MAX_TRIANGLE_COUNT = 100000


def _get_triangles_in_polygons(object: bpy.types.Object) -> int:
    triangle_count = 0
    with suppress(AttributeError):
        for p in object.data.polygons:
            count = p.loop_total
            if count > 2:
                triangle_count += count - 2
    return triangle_count


def _get_triangle_count(object_name: str):
    triangle_count = 0
    object = bpy.data.objects[object_name]
    triangle_count += _get_triangles_in_polygons(object)
    decimateIdx = -1
    
    for modifierIdx, modifier in enumerate(list(object.modifiers)):
        if modifier.type == 'DECIMATE':
            triangle_count = modifier.face_count
            decimateIdx = modifierIdx

    for modifierIdx, modifier in enumerate(list(object.modifiers)):
        if modifier.type == 'MIRROR' and modifierIdx > decimateIdx:
            if modifier.use_x:
                triangle_count *= 2
            if modifier.use_y:
                triangle_count *= 2
            if modifier.use_z:
                triangle_count *= 2
    return triangle_count


def _get_object_list(asset_type: AssetType, export_data: dict):
    if asset_type == AssetType.model:
        return export_data.get('models', [])
    elif asset_type == AssetType.scene:
        scene_name = export_data.get('scene')
        scene = bpy.data.scenes[scene_name]
        return scene.objects.keys()
    return []


def check_triangle_count(asset_type: AssetType, export_data: dict) -> Tuple[bool, str]:
    """Check if triangle count is less than 100k.

    Parameters:
        asset_type: type of asset that will be uploaded
        export_data: dict containing objects to be uploaded info

    Returns:
        is_valid, message: if check passed and a report message
    """
    logging.info('Running triangle count...')
    triangle_count = 0
    object_list = _get_object_list(asset_type, export_data)
    for obj in object_list:
        triangle_count += _get_triangle_count(obj)
    message = f'Asset has {triangle_count} triangles'

    logging.info(message)
    return triangle_count <= MAX_TRIANGLE_COUNT, message


name = 'Triangle count'
description = 'Checks if asset has less than 100k triangles'
triangle_count = BaseValidator(name, Category.warning, description, check_triangle_count)
