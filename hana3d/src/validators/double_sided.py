"""Double sided Validator."""

import logging
from typing import List, Tuple

import bpy

from . import BaseValidator, Category
from ..asset.asset_type import AssetType


def _check_backface_culling(material: bpy.types.Material) -> bool:
    return material.use_backface_culling


def _get_incorrect_materials_in_objects(models: List[str]) -> List[str]:
    materials = []
    for model in models:
        for mat_slot in bpy.data.objects[model].material_slots:
            if not _check_backface_culling(mat_slot.material):
                materials.append(mat_slot.material.name)
    return materials


def _get_incorrect_materials(asset_type: AssetType, export_data: dict):
    if asset_type == AssetType.model:
        return _get_incorrect_materials_in_objects(export_data.get('models', []))
    if asset_type == AssetType.scene:
        scene_name = export_data.get('scene')
        scene = bpy.data.scenes[scene_name]
        return _get_incorrect_materials_in_objects(scene.objects.keys())
    if asset_type == AssetType.material:
        material = bpy.data.materials[export_data.get('material')]
        if not _check_backface_culling(material):
            return [material.name]


def fix_double_sided(asset_type: AssetType, export_data: dict):
    """Remove all inactive UV layers from export data.

    Parameters:
        asset_type: type of asset that will be uploaded
        export_data: dict containing objects to be uploaded info

    """
    materials = _get_incorrect_materials(asset_type, export_data)
    for material in materials:
        bpy.data.materials[material].use_backface_culling = True


def check_double_sided(asset_type: AssetType, export_data: dict) -> Tuple[bool, str]:
    """Check for duplicated UV layers in a single mesh on export data.

    Parameters:
        asset_type: type of asset that will be uploaded
        export_data: dict containing objects to be uploaded info

    Returns:
        is_valid, message: if check passed and a report message
    """
    logging.info('Running Double Sided validator...')
    is_valid = True
    message = 'All materials have backface culling enabled!'

    incorrect_materials = _get_incorrect_materials(asset_type, export_data)
    if incorrect_materials:
        message = f'Materials with backface culling disabled: {", ".join(incorrect_materials)}'
        is_valid = False

    logging.info(message)
    return is_valid, message


name = 'Double Sided Check'
description = 'Checks for backface culling setting on materials'
double_sided = BaseValidator(
    name,
    Category.error,
    description,
    check_double_sided,
    fix_double_sided,
)
