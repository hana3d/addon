"""Auxiliary search functions."""
import os
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

import bpy

from ..asset.asset_type import AssetType
from ... import paths, utils
from ...config import (
    HANA3D_MATERIALS,
    HANA3D_MODELS,
    HANA3D_NAME,
    HANA3D_SCENES,
    HANA3D_UI,
)


@dataclass
class SearchResult(object):
    """Hana3D search result."""

    thumbnail: str
    thumbnail_small: str
    download_url: str
    id: str  # noqa: WPS125
    view_id: str
    name: str
    asset_type: AssetType
    tooltip: str
    tags: List[str]
    verification_status: str
    author_id: str
    description: str
    render_jobs: List[str]
    workspace: str
    downloaded: float = 0
    metadata: Dict = field(default_factory=dict)
    created: str = ''
    libraries: List[Dict] = field(default_factory=list)
    bbox_min: Tuple[float, float, float] = (-0.5, -0.5, 0.0)
    bbox_max: Tuple[float, float, float] = (0.5, 0.5, 1.0)


def load_previews(asset_type: AssetType, search_results: Dict):
    """Load small preview thumbnails for search results.

    Parameters:
        asset_type: type of the asset
        search_results: search results
    """
    mappingdict = {
        'MODEL': 'model',
        'SCENE': 'scene',
        'MATERIAL': 'material',
    }

    directory = paths.get_temp_dir(f'{mappingdict[asset_type]}_search')
    if search_results is None:
        return

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


def get_search_results(asset_type: AssetType = None) -> List[SearchResult]:
    """Get search results.

    Parameters:
        asset_type: type of the assets searched

    Returns:
        List: search results
    """
    if asset_type is None:
        asset_type = _get_asset_type_from_ui()
    if f'{HANA3D_NAME}_{asset_type}_search' not in bpy.context.window_manager:
        return []
    return bpy.context.window_manager.get(f'{HANA3D_NAME}_{asset_type}_search')


def set_search_results(asset_type: AssetType, results_value: List[SearchResult]):
    """Set search results for given asset type.

    Parameters:
        asset_type: asset type
        results_value: search results
    """
    bpy.context.window_manager[f'{HANA3D_NAME}_{asset_type}_search'] = results_value


def get_original_search_results(asset_type: AssetType = None):
    """Get original search results.

    Parameters:
        asset_type: type of the assets searched

    Returns:
        List: original search results
    """
    if asset_type is None:
        asset_type = _get_asset_type_from_ui()
    if f'{HANA3D_NAME}_{asset_type}_search_original' not in bpy.context.window_manager:
        return {}
    return bpy.context.window_manager[f'{HANA3D_NAME}_{asset_type}_search_original']


def set_original_search_results(asset_type: AssetType, results_value: Dict):
    """Set original search results for given asset type.

    Parameters:
        asset_type: asset type
        results_value: original search results
    """
    if asset_type is None:
        asset_type = _get_asset_type_from_ui()
    bpy.context.window_manager[f'{HANA3D_NAME}_{asset_type}_search_original'] = results_value


def get_search_props(asset_type: AssetType = None):
    """Get search props.

    Parameters:
        asset_type: asset type currently being searched

    Returns:
        Dict | None: search props if available
    """
    if asset_type is None:
        asset_type = _get_asset_type_from_ui()
    if asset_type == 'model' and hasattr(bpy.context.window_manager, HANA3D_MODELS):  # noqa : WPS421
        return getattr(bpy.context.window_manager, HANA3D_MODELS)
    elif asset_type == 'scene' and hasattr(bpy.context.window_manager, HANA3D_SCENES):  # noqa : WPS421
        return getattr(bpy.context.window_manager, HANA3D_SCENES)
    elif asset_type == 'material' and hasattr(bpy.context.window_manager, HANA3D_MATERIALS):  # noqa : WPS421
        return getattr(bpy.context.window_manager, HANA3D_MATERIALS)


def run_operator(get_next=False):
    """Run search operator.

    Parameters:
        get_next: get next batch of results
    """
    search_op = getattr(bpy.ops.view3d, f'{HANA3D_NAME}_search')
    search_op(get_next=get_next)


def _get_asset_type_from_ui() -> AssetType:
    uiprops = getattr(bpy.context.window_manager, HANA3D_UI)
    return uiprops.asset_type.lower()
