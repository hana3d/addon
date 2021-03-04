"""Vertex Color Validator."""

import logging
from typing import List, Tuple

import bpy

from . import BaseValidator, Category
from ..asset.asset_type import AssetType


def _get_morph_target_meshes(models: List[str]) -> List[str]:
    meshes = []
    for model in models:
        blend_object = bpy.data.objects[model]
        if blend_object.type == 'MESH' and blend_object.data.shape_keys:
            meshes.append(model)
    return meshes


def _get_incorrect_meshes(asset_type: AssetType, export_data: dict):
    if asset_type == AssetType.model:
        return _get_morph_target_meshes(export_data.get('models', []))
    if asset_type == AssetType.scene:
        scene_name = export_data.get('scene')
        scene = bpy.data.scenes[scene_name]
        return _get_morph_target_meshes(scene.objects.keys())
    if asset_type == AssetType.material:
        return []


def fix_morph_target(asset_type: AssetType, export_data: dict):
    """Remove all shape keys from export data.

    Parameters:
        asset_type: type of asset that will be uploaded
        export_data: dict containing objects to be uploaded info

    """
    meshes = _get_incorrect_meshes(asset_type, export_data)
    view_layer = bpy.context.view_layer
    for mesh in meshes:
        view_layer.objects.active = bpy.data.objects[mesh]
        bpy.ops.object.shape_key_remove(all=True)


def check_morph_target(asset_type: AssetType, export_data: dict) -> Tuple[bool, str]:
    """Check for shape keys in all meshes on export data.

    Parameters:
        asset_type: type of asset that will be uploaded
        export_data: dict containing objects to be uploaded info

    Returns:
        is_valid, message: if check passed and a report message
    """
    logging.info('Running Morph Target validator...')
    is_valid = True
    message = 'All meshes have no shape keys.'

    incorrect_meshes = _get_incorrect_meshes(asset_type, export_data)
    if incorrect_meshes:
        message = f'Meshes with shape keys: {", ".join(incorrect_meshes)}'
        is_valid = False

    logging.info(message)
    return is_valid, message


name = 'Morph Target Check'
description = 'Checks for shape keys on objects'
morph_target_checker = BaseValidator(
    name,
    Category.error,
    description,
    check_morph_target,
    fix_morph_target,
)
