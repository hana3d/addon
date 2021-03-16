"""Missing references Validator."""
import logging
import os
from contextlib import suppress
from typing import List, Set, Tuple

import bpy

from . import BaseValidator, Category
from ..asset.asset_type import AssetType


def _check_missing_reference(image: bpy.types.Image):
    path = image.filepath_from_user()
    return os.path.exists(path)


def _get_missing_textures_in_material(material: bpy.types.Material) -> Set[str]:
    textures: Set[str] = set()
    for node in material.node_tree.nodes:
        if node.type == 'TEX_IMAGE' and not _check_missing_reference(node.image):
            textures.add(node.image.name)    # noqa: WPS220
    return textures


def _get_missing_textures_in_objects(models: List[str]) -> Set[str]:
    textures: Set[str] = set()
    with suppress(AttributeError):
        for model in models:
            for mat_slot in bpy.data.objects[model].material_slots:
                textures = textures.union(_get_missing_textures_in_material(mat_slot.material))
    return textures


def _get_missing_texture_names(asset_type: AssetType, export_data: dict):
    if asset_type == AssetType.model:
        return _get_missing_textures_in_objects(export_data.get('models', []))
    if asset_type == AssetType.scene:
        scene_name = export_data.get('scene')
        scene = bpy.data.scenes[scene_name]
        return _get_missing_textures_in_objects(scene.objects.keys())
    if asset_type == AssetType.material:
        material = bpy.data.materials[export_data.get('material')]
        return _get_missing_textures_in_material(material)


def fix_textures_references(asset_type: AssetType, export_data: dict):
    """Remove missing textures references.

    Parameters:
        asset_type: type of asset that will be uploaded
        export_data: dict containing objects to be uploaded info

    """
    missing_textures = _get_missing_texture_names(asset_type, export_data)
    for texture_name in missing_textures:
        texture = bpy.data.images[texture_name]
        bpy.data.images.remove(texture)


def check_textures_references(asset_type: AssetType, export_data: dict) -> Tuple[bool, str]:
    """Check if any of the texture references are missing.

    Parameters:
        asset_type: type of asset that will be uploaded
        export_data: dict containing objects to be uploaded info

    Returns:
        is_valid, message: if check passed and a report message
    """
    logging.info('Running Missing Textures Check...')
    is_valid = True
    message = 'All referenced textures exist!'

    missing_textures = _get_missing_texture_names(asset_type, export_data)
    if missing_textures:
        message = f'Textures missing: {", ".join(missing_textures)}'
        is_valid = False

    logging.info(message)
    return is_valid, message


name = 'Missing References'
description = 'Checks referenced textures exist'
missing_references_check = BaseValidator(
    name,
    Category.error,
    description,
    check_textures_references,
    fix_textures_references,
)
