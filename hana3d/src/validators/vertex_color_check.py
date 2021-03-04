"""Vertex Color Validator."""

import logging
from typing import List, Tuple

import bpy

from . import BaseValidator, Category
from ..asset.asset_type import AssetType


def _get_vertex_color_meshes(models: List[str]) -> List[str]:
    meshes = []
    for model in models:
        blend_object = bpy.data.objects[model]
        if blend_object.type == 'MESH' and blend_object.data.vertex_colors:
            meshes.append(model)
    return meshes


def _get_incorrect_meshes(asset_type: AssetType, export_data: dict):
    if asset_type == AssetType.model:
        return _get_vertex_color_meshes(export_data.get('models', []))
    if asset_type == AssetType.scene:
        scene_name = export_data.get('scene')
        scene = bpy.data.scenes[scene_name]
        return _get_vertex_color_meshes(scene.objects.keys())
    if asset_type == AssetType.material:
        return []


def fix_vertex_color(asset_type: AssetType, export_data: dict):
    """Remove all vertex colors from export data.

    Parameters:
        asset_type: type of asset that will be uploaded
        export_data: dict containing objects to be uploaded info

    """
    meshes = _get_incorrect_meshes(asset_type, export_data)
    for mesh in meshes:
        mesh_data = bpy.data.objects[mesh].data
        vertex_colors = mesh_data.vertex_colors
        while vertex_colors:
            vertex_colors.remove(vertex_colors[0])


def check_vertex_color(asset_type: AssetType, export_data: dict) -> Tuple[bool, str]:
    """Check for vertex color in all meshes on export data.

    Parameters:
        asset_type: type of asset that will be uploaded
        export_data: dict containing objects to be uploaded info

    Returns:
        is_valid, message: if check passed and a report message
    """
    logging.info('Running Vertex Color validator...')
    is_valid = True
    message = 'All meshes have no vertex colors.'

    incorrect_meshes = _get_incorrect_meshes(asset_type, export_data)
    if incorrect_meshes:
        message = f'Meshes with vertex colors: {", ".join(incorrect_meshes)}'
        is_valid = False

    logging.info(message)
    return is_valid, message


name = 'Vertex Color Check'
description = 'Checks for vertex color setting on objects'
vertex_color_checker = BaseValidator(
    name,
    Category.error,
    description,
    check_vertex_color,
    fix_vertex_color,
)
