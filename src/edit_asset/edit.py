"""Edit functions."""
import bpy

from ...config import HANA3D_ASSET
from ..libraries.libraries import set_library_props
from ..search.search import get_search_results
from ..tags.tags import update_tags_list


def get_edit_props():
    """Get edit props of the selected asset in search.

    Returns:
        edit props
    """
    return getattr(bpy.context.window_manager, HANA3D_ASSET)


def set_edit_props(asset_index: int):
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
    asset_props.asset_type = asset_data.asset_type

    if asset_data.tags:
        update_tags_list(asset_props, bpy.context)
        for tag in asset_data.tags:
            asset_props.tags_list[tag].selected = True

    if asset_data.libraries:
        set_library_props(asset_data, asset_props)
