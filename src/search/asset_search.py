"""Asset Search."""
from dataclasses import dataclass
from typing import Dict, List

from bpy.types import Context

from ..asset.asset_type import AssetType
from ...config import HANA3D_NAME


@dataclass
class SearchResult(object):
    """Hana3D search result."""

    view_id: str
    file_name: str
    download_url: str
    asset_type: AssetType

class AssetSearch(object):
    """Hana3D search information by asset type."""

    def __init__(self, context: Context, asset_type: AssetType):
        """Create a Search object by asset type.

        Args:
            context: Blender context.
            asset_type: an asset type
        """
        self.context = context
        self.asset_type = asset_type

    def get_results(self) -> List[SearchResult]:
        """Get search results by asset type.

        Returns:
            List: search results by asset type
        """
        return self.context.window_manager.get(f'{HANA3D_NAME}_{self.asset_type}_search')

    def get_original_results(self) -> List[Dict]:
        """Get original search results by asset type (TODO: refactor this logic).

        Returns:
            List: original search results by asset type
        """
        return self.context.window_manager.get(f'{HANA3D_NAME}_{self.asset_type}_search_orig')

    def set_results(self, results: List[SearchResult]):  # noqa : WPS110
        self.results = results
        self.context.window_manager[f'{HANA3D_NAME}_{self.asset_type}_search'] = results

    def set_original_results(self, original_results: List[Dict]):
        self.original_results = original_results
        self.context.window_manager[f'{HANA3D_NAME}_{self.asset_type}_search_orig'] = original_results
