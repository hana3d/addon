"""Auxiliary search functions."""
import logging
import os
from dataclasses import asdict, dataclass, field
from typing import Dict, List, Tuple

import bpy

from ... import paths, utils
from ...config import (
    HANA3D_MATERIALS,
    HANA3D_MODELS,
    HANA3D_NAME,
    HANA3D_SCENES,
    HANA3D_UI,
)
from ..asset.asset_type import AssetType
from ..metaclasses.singleton import Singleton


@dataclass
class AssetData(object):
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
    revision: str = ''
    libraries: List[Dict] = field(default_factory=list)
    bbox_min: Tuple[float, float, float] = (-0.5, -0.5, 0.0)
    bbox_max: Tuple[float, float, float] = (0.5, 0.5, 1.0)
    file_name: str = ''

    def copy(self):
        """Create copy of object.

        Returns:
            AssetData: copied object
        """
        return AssetData(**asdict(self))


class SearchData(object, metaclass=Singleton):
    """Hana3D Blender Search Data singleton class."""

    search_results: Dict[AssetType, List[AssetData]]
    original_search_results: Dict[AssetType, Dict]

    def __init__(self) -> None:
        """Create a new UI instance."""
        self.search_results = {
            AssetType.model: [],
            AssetType.material: [],
            AssetType.scene: [],
        }
        self.original_search_results = {
            AssetType.model: {},
            AssetType.material: {},
            AssetType.scene: {},
        }


def load_preview(asset_type: AssetType, search_result: AssetData, index: int):
    """Load small preview thumbnails for search results.

    Parameters:
        asset_type: type of the asset
        search_result: asset data
        index: preview number
    """
    directory = paths.get_temp_dir(f'{asset_type}_search')
    if search_result is None:
        return

    logging.debug('Loading preview')
    if search_result.thumbnail_small == '':
        logging.debug('No small thumbnail, will load placeholder')
        load_placeholder_thumbnail(index, search_result.id)
        return

    thumbnail_path = os.path.join(directory, search_result.thumbnail_small)
    image_name = utils.previmg_name(index)
    logging.debug(f'Loading {image_name} in {thumbnail_path}')

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
    else:
        logging.error('No thumbnail')


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


def get_search_results(asset_type: AssetType = None) -> List[AssetData]:
    """Get search results.

    Parameters:
        asset_type: type of the assets searched

    Returns:
        List: search results
    """
    if asset_type is None:
        asset_type = _get_asset_type_from_ui()
    return SearchData().search_results[asset_type]


def set_search_results(asset_type: AssetType, results_value: List[AssetData]):
    """Set search results for given asset type.

    Parameters:
        asset_type: asset type
        results_value: search results
    """
    SearchData().search_results[asset_type] = results_value


def get_original_search_results(asset_type: AssetType = None) -> Dict:
    """Get original search results.

    Parameters:
        asset_type: type of the assets searched

    Returns:
        Dict: original search results
    """
    if asset_type is None:
        asset_type = _get_asset_type_from_ui()
    return SearchData().original_search_results[asset_type]


def set_original_search_results(asset_type: AssetType, results_value: Dict):
    """Set original search results for given asset type.

    Parameters:
        asset_type: asset type
        results_value: original search results
    """
    SearchData().original_search_results[asset_type] = results_value


def get_search_props(asset_type: AssetType = None):
    """Get search props.

    Parameters:
        asset_type: asset type currently being searched

    Returns:
        Dict | None: search props if available
    """
    if asset_type is None:
        asset_type = _get_asset_type_from_ui()
    if asset_type == AssetType.model and hasattr(bpy.context.window_manager, HANA3D_MODELS):  # noqa : WPS421
        return getattr(bpy.context.window_manager, HANA3D_MODELS)
    elif asset_type == AssetType.scene and hasattr(bpy.context.window_manager, HANA3D_SCENES):  # noqa : WPS421
        return getattr(bpy.context.window_manager, HANA3D_SCENES)
    elif asset_type == AssetType.material and hasattr(bpy.context.window_manager, HANA3D_MATERIALS):  # noqa : WPS421
        return getattr(bpy.context.window_manager, HANA3D_MATERIALS)


def run_operator(get_next=False):
    """Run search operator.

    Parameters:
        get_next: get next batch of results
    """
    search_props = get_search_props()
    if not search_props.is_searching:
        search_props.is_searching = True
        logging.debug(f'Running search operator with get_next = {get_next}')
        search_op = getattr(bpy.ops.view3d, f'{HANA3D_NAME}_search')
        search_op(get_next=get_next)


def _get_asset_type_from_ui() -> AssetType:
    uiprops = getattr(bpy.context.window_manager, HANA3D_UI)
    return uiprops.asset_type_search.lower()
