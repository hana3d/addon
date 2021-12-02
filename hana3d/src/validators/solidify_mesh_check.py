"""Solidify mesh Validator."""

import logging
from typing import List, Tuple

import bpy

from . import BaseValidator, Category
from ..asset.asset_type import AssetType

MODIFIER_NAME = 'SOLIDIFY'


def _check_solidify(blend_object: bpy.types.Object) -> bool:
    for mod in blend_object.modifiers:
        if mod.type == MODIFIER_NAME:
            return True
    return False


def _get_solidify_modifiers(models: List[str]) -> List[str]:
    objects = [] # noqa: WPS110
    for model in models:
        blend_object = bpy.data.objects[model]
        if _check_solidify(blend_object):
            objects.append(model)
    return objects


def _get_object_list(asset_type: AssetType, export_data: dict):
    if asset_type == AssetType.model:
        return export_data.get('models', [])
    if asset_type == AssetType.scene:
        scene_name = export_data.get('scene')
        scene = bpy.data.scenes[scene_name]
        return scene.objects.keys()
    return []


def check_solidify_meshes(asset_type: AssetType, export_data: dict) -> Tuple[bool, str]:
    """Checks if there are meshes with solidify.

    Parameters:
        asset_type: type of asset that will be uploaded
        export_data: dict containing objects to be uploaded info

    Returns:
        is_valid, message: if check passed and a report message
    """
    logging.info('Running solidify meshes check...')
    is_valid = True
    message = 'Asset has no solidify meshes'

    object_list = _get_object_list(asset_type, export_data)
    models_list = _get_solidify_modifiers(object_list)

    if models_list:
        message = f'Meshes with solidify modifier: {", ".join(models_list)}'
        is_valid = False

    logging.info(message)
    return is_valid, message


name = 'Solidify meshes check'
description = 'Checks if there are meshes with solidify'
solidify_mesh_check = BaseValidator(name, Category.warning, description, check_solidify_meshes)