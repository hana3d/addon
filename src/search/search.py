"""Auxiliary search functions."""
import json
import logging
import os
import pathlib
import tempfile
import uuid
from dataclasses import dataclass
from typing import Dict, List, Tuple

import bpy
from bpy.props import BoolProperty, StringProperty
from bpy.types import Context

from .asset_search import AssetSearch
from ..asset.asset_type import AssetType
from ... import hana3d_oauth, paths, utils
from ...config import (
    HANA3D_MATERIALS,
    HANA3D_MODELS,
    HANA3D_NAME,
    HANA3D_SCENES,
    HANA3D_UI,
)


def check_errors(request_data: Dict) -> Tuple[bool, str]:
    if request_data.get('status_code') == 401:
        logging.debug(request_data)
        if request_data.get('code') == 'token_expired':
            user_preferences = bpy.context.preferences.addons[HANA3D_NAME].preferences
            if user_preferences.api_key != '':
                hana3d_oauth.refresh_token(immediate=False)
                return False, request_data.get('description', '')
            return False, 'Missing or wrong api_key in addon preferences'
    elif request_data.get('status_code') == 403:
        logging.debug(request_data)
        if request_data.get('code') == 'invalid_permissions':
            return False, request_data.get('description', '')
    return True, ''


def load_previews(asset_type: AssetType, asset_search: AssetSearch):
    mappingdict = {
        'MODEL': 'model',
        'SCENE': 'scene',
        'MATERIAL': 'material',
    }

    directory = paths.get_temp_dir(f'{mappingdict[asset_type]}_search')
    search_results = asset_search.original_results

    if search_results is not None:
        index = 0
        for search_result in search_results:
            if search_result['thumbnail_small'] == '':
                load_placeholder_thumbnail(index, search_result['id'])
                index += 1
                continue

            thumbnail_path = os.path.join(directory, search_result['thumbnail_small'])

            image_name = utils.previmg_name(index)

            if os.path.exists(thumbnail_path):  # sometimes we are unlucky...
                img = bpy.data.images.get(image_name)
                if img is None:
                    img = bpy.data.images.load(thumbnail_path)
                    img.name = image_name
                elif img.filepath != thumbnail_path:
                    # had to add this check for autopacking files...
                    if img.packed_file is not None:
                        img.unpack(method='USE_ORIGINAL')
                    img.filepath = thumbnail_path
                    img.reload()
                img.colorspace_settings.name = 'Linear'
            index += 1

    def load_placeholder_thumbnail(index: int, asset_id: str):
        """Load placeholder thumbnail for assets without one.

        Parameters:
            index: index number of the asset in search results
            asset_id: asset id
        """
        placeholder_path = paths.get_addon_thumbnail_path('thumbnail_notready.png')

        img = bpy.data.images.load(placeholder_path)
        img.name = utils.previmg_name(index)

        hidden_img = bpy.data.images.load(placeholder_path)
        hidden_img.name = f'.{asset_id}'

        fullsize_img = bpy.data.images.load(placeholder_path)
        fullsize_img.name = utils.previmg_name(index, fullsize=True)
