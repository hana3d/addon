"""UV Check Validator."""

import logging
from typing import List, Tuple

import bpy

from . import BaseValidator, Category
from ..asset.asset_type import AssetType


def _get_multiple_uv_models(models: List[str]) -> List[str]:
    return [
        model for model in models
        if (
            bpy.data.objects[model].data is not None
            and hasattr(bpy.data.objects[model].data, 'uv_layers')  # noqa: WPS421
            and len(bpy.data.objects[model].data.uv_layers) > 1  # noqa: WPS219
        )
    ]


def _get_object_list(asset_type: AssetType, export_data: dict):
    if asset_type == AssetType.model:
        return export_data.get('models', [])
    if asset_type == AssetType.scene:
        scene_name = export_data.get('scene')
        scene = bpy.data.scenes[scene_name]
        return scene.objects.keys()
    return []


def fix_uv_layers(asset_type: AssetType, export_data: dict):
    """Remove all inactive UV layers from export data.

    Parameters:
        asset_type: type of asset that will be uploaded
        export_data: dict containing objects to be uploaded info

    """
    models = _get_object_list(asset_type, export_data)
    multiple_uv_models = _get_multiple_uv_models(models)
    for model in multiple_uv_models:
        model_data = bpy.data.objects[model]
        uv_layers = model_data.data.uv_layers
        unwanted_uvs = [
            uv for uv in uv_layers if not uv.active_render
        ]
        while unwanted_uvs:
            uv_layers.remove(unwanted_uvs.pop())


def check_uv_layers(asset_type: AssetType, export_data: dict) -> Tuple[bool, str]:
    """Check for duplicated UV layers in a single mesh on export data.

    Parameters:
        asset_type: type of asset that will be uploaded
        export_data: dict containing objects to be uploaded info

    Returns:
        is_valid, message: if check passed and a report message
    """
    logging.info('Running UV Check...')
    is_valid = True
    message = 'No duplicated UVs detected!'

    models = _get_object_list(asset_type, export_data)
    multiple_uv_models = _get_multiple_uv_models(models)
    if multiple_uv_models:
        message = f'Meshes with more than 1 UV Map: {", ".join(multiple_uv_models)}'
        is_valid = False

    logging.info(message)
    return is_valid, message


name = 'UV Check'
description = 'Checks for multiple UVs in a mesh'
uv_checker = BaseValidator(name, Category.error, description, check_uv_layers, fix_uv_layers)
