"""Search operator."""

import logging
from typing import List, Tuple

import bpy

from . import BaseValidator, Category
from ..upload.export_data import get_export_data
from ..upload.upload import get_upload_props


def _get_multiple_uv_models(models: List[str]) -> List[str]:
    return [
        model for model in models
        if (
            bpy.data.objects[model].data is not None
            and hasattr(bpy.data.objects[model].data, 'uv_layers')  # noqa: WPS421
            and len(bpy.data.objects[model].data.uv_layers) > 1  # noqa: WPS219
        )
    ]


def fix_uv_layers():
    """Remove all inactive UV layers from export data."""
    props = get_upload_props()
    export_data, _ = get_export_data(props)
    logging.info(f'Export data: {export_data}')
    models = export_data.get('models', [])
    multiple_uv_models = _get_multiple_uv_models(models)
    for model in multiple_uv_models:
        model_data = bpy.data.objects[model]
        uv_layers = model_data.data.uv_layers
        unwanted_uvs = [
            uv for uv in uv_layers
            if uv != uv_layers.active
        ]
        while unwanted_uvs:
            uv_layers.remove(unwanted_uvs.pop())


def check_uv_layers() -> Tuple[bool, str]:
    """Check for duplicated UV layers in a single mesh on export data.

    Returns:
        is_valid, message: if check passed and a report message
    """
    logging.info('Running UV Check...')
    is_valid = True
    message = 'No duplicated UVs detected!'

    props = get_upload_props()
    export_data, _ = get_export_data(props)
    logging.info(f'Export data: {export_data}')
    models = export_data.get('models', [])
    multiple_uv_models = _get_multiple_uv_models(models)
    if multiple_uv_models:
        message = f'Meshes with more than 1 UV Map: {", ".join(multiple_uv_models)}'
        is_valid = False

    logging.info(message)
    return is_valid, message


name = 'UV Check'
description = 'Checks for multiple UVs in a mesh'
uv_checker = BaseValidator(name, Category.warning, description, check_uv_layers, fix_uv_layers)
