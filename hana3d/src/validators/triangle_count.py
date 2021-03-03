"""Triangle count Validator."""

import logging
from contextlib import suppress
from typing import Tuple

import bpy

from . import BaseValidator, Category
from ..asset.asset_type import AssetType

MAX_TRIANGLE_COUNT = 100000


def _get_triangles_in_polygons(blend_object: bpy.types.Object) -> int:
    triangle_count = 0
    with suppress(AttributeError):
        for polygon in blend_object.data.polygons:
            count = polygon.loop_total
            if count > 2:
                triangle_count += count - 2
    return triangle_count


def _get_triangle_count(object_name: str):
    blend_object = bpy.data.objects[object_name]
    triangle_count = _get_triangles_in_polygons(blend_object)
    decimate_index = -1

    for modifier_index, modifier in enumerate(list(blend_object.modifiers)):
        if modifier.type == 'DECIMATE':
            triangle_count = modifier.face_count
            decimate_index = modifier_index

        elif modifier.type == 'MIRROR' and modifier_index > decimate_index:
            for axis in modifier.use_axis:
                if axis:
                    triangle_count *= 2
            # TODO: Deal with bisect
        
        # TODO: Check if other modifiers affect triangle count
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
    for blend_object in object_list:
        triangle_count = triangle_count + _get_triangle_count(blend_object)
    message = f'Asset has {triangle_count} triangles'

    logging.info(message)
    return triangle_count <= MAX_TRIANGLE_COUNT, message


name = 'Triangle count'
description = 'Checks if asset has less than 100k triangles'
triangle_count = BaseValidator(name, Category.warning, description, check_triangle_count)
