"""Asset Search."""
from typing import List

from bpy.types import Context

from .search import SearchResult
from ..asset.asset_type import AssetType
from ...config import HANA3D_NAME


class AssetSearch(object):
    """Hana3D search information by asset type (TODO: merge this class with `Search`)."""

    def __init__(self, context: Context, asset_type: AssetType):
        """Create a Search object by asset type.

        Args:
            context: Blender context.
            asset_type: an asset type
        """
        self.context = context
        self.asset_type = asset_type

    @property  # noqa : WPS110
    def results(self) -> List[SearchResult]:  # noqa : WPS110
        """Get search results by asset type.

        Returns:
            List: search results by asset type
        """
        return self.context.window_manager.get(f'{HANA3D_NAME}_{self.asset_type}_search')

    @property
    def results_orig(self) -> List[SearchResult]:
        """Get original search results by asset type (TODO: refactor this logic).

        Returns:
            List: original search results by asset type
        """
        return self.context.window_manager.get(f'{HANA3D_NAME}_{self.asset_type}_search_orig')

    @results.setter  # noqa : WPS110
    def results(self, results: List[SearchResult]):  # noqa : WPS110
        self.context.window_manager[f'{HANA3D_NAME}_{self.asset_type}_search'] = results

    @results_orig.setter
    def results_orig(self, results_orig: List[SearchResult]):
        self.context.window_manager[f'{HANA3D_NAME}_{self.asset_type}_search_orig'] = results_orig
