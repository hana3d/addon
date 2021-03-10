"""Triangle count Validator."""

import logging
from typing import List, Tuple

import bpy

from . import BaseValidator, Category
from ..asset.asset_type import AssetType

MAX_TRIANGLE_COUNT = 100000


def _get_triangles_in_mesh(mesh: bpy.types.Mesh) -> int:
    triangle_count = 0
    for polygon in mesh.polygons:
        count = len(polygon.vertices)
        if count > 2:
            triangle_count += count - 2
    return triangle_count


def _get_triangle_count(object_names: List[str]) -> int:
    object_data = set()
    triangle_count = 0
    for object_name in object_names:
        blend_object = bpy.data.objects[object_name]
        if blend_object.type == 'MESH' and blend_object.data not in object_data:
            object_data.add(blend_object.data)
            depsgraph = bpy.context.evaluated_depsgraph_get()
            object_eval = blend_object.evaluated_get(depsgraph)
            mesh_from_eval = bpy.data.meshes.new_from_object(object_eval)
            triangle_count += _get_triangles_in_mesh(mesh_from_eval)
            bpy.data.meshes.remove(mesh_from_eval)
    return triangle_count


def _get_object_list(asset_type: AssetType, export_data: dict):
    if asset_type == AssetType.model:
        return export_data.get('models', [])
    if asset_type == AssetType.scene:
        scene_name = export_data.get('scene')
        scene = bpy.data.scenes[scene_name]
        return scene.objects.keys()
    return []


def check_triangle_count(asset_type: AssetType, export_data: dict) -> Tuple[bool, str]:
    """Check if triangle count is less than MAX_TRIANGLE_COUNT.

    Parameters:
        asset_type: type of asset that will be uploaded
        export_data: dict containing objects to be uploaded info

    Returns:
        is_valid, message: if check passed and a report message
    """
    logging.info('Running triangle count...')
    triangle_count = 0
    object_list = _get_object_list(asset_type, export_data)
    triangle_count = _get_triangle_count(object_list)
    message = f'Asset has {triangle_count} triangles'

    logging.info(message)
    return triangle_count <= MAX_TRIANGLE_COUNT, message


name = 'Triangle count'
description = f'Checks if asset has triangle count <= {MAX_TRIANGLE_COUNT}'
triangle_count = BaseValidator(name, Category.warning, description, check_triangle_count)
