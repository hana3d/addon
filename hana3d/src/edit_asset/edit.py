"""Edit functions."""
import os
import shutil
from contextlib import suppress

import bpy

from ..libraries.libraries import (
    clear_libraries,
    set_library_props,
    update_libraries_list,
)
from ..search.search import get_search_results
from ..tags.tags import clear_tags, update_tags_list
from ... import paths
from ...config import HANA3D_ASSET


def get_edit_props():
    """Get edit props.

    Returns:
        edit props
    """
    return getattr(bpy.context.window_manager, HANA3D_ASSET)


def set_edit_props(asset_index: int):
    """Set edit props for the selected asset in search.

    Parameters:
        asset_index: index of asset in search results
    """
    asset_props = get_edit_props()
    search_results = get_search_results()
    asset_data = search_results[asset_index]
    asset_props.clear_data()

    asset_props.id = asset_data.id  # noqa: WPS125
    asset_props.view_id = asset_data.view_id
    asset_props.view_workspace = asset_data.workspace
    asset_props.name = asset_data.name
    asset_props.tags = ','.join(asset_data.tags)
    asset_props.description = asset_data.description
    asset_props.asset_type = asset_data.asset_type.upper()
    asset_props.asset_index = asset_index

    clear_tags(asset_props)
    update_tags_list(asset_props, bpy.context)
    for tag in asset_data.tags:
        asset_props.tags_list[tag].selected = True

    if asset_data.libraries:
        clear_libraries(asset_props)
        update_libraries_list(asset_props, bpy.context)
        set_library_props(asset_data.libraries, asset_props)

    _set_thumbnail(asset_data, asset_props)


def _set_thumbnail(asset_data, asset_props):
    if asset_data.thumbnail == '':
        asset_props.thumbnail = ''
    else:
        thumbnail_name = asset_data.thumbnail.split(os.sep)[-1]  # noqa: WPS204
        tempdir = paths.get_temp_dir(f'{asset_data.asset_type}_search')  # noqa: WPS204
        thumbpath = os.path.join(tempdir, thumbnail_name)
        asset_thumbs_dir = paths.get_download_dirs(asset_data.asset_type)[0]
        asset_thumb_path = os.path.join(asset_thumbs_dir, thumbnail_name)
        with suppress(FileNotFoundError):
            shutil.copy(thumbpath, asset_thumb_path)
        asset_props.thumbnail = asset_thumb_path
