"""Search."""

from dataclasses import dataclass
from ..asset.asset_type import AssetType
from typing import List

from bpy.types import Context

from ...config import HANA3D_NAME


@dataclass
class SearchResult(object):
    """Hana3D search result."""

    view_id: str
    file_name: str
    download_url: str
    asset_type: AssetType


class Search(object):
    """Hana3D search information."""

    def __init__(self, context: Context):
        """Create a Search object.

        Args:
            context: Blender context.
        """
        self.context = context

    @property  # noqa : WPS110
    def results(self) -> List[SearchResult]:  # noqa : WPS110
        """Get search results.

        Returns:
            List: search results
        """
        if f'{HANA3D_NAME}_search_results' not in self.context.window_manager:
            return []
        return self.context.window_manager[f'{HANA3D_NAME}_search_results']

    @property
    def results_orig(self) -> List[SearchResult]:
        """Get original search results (FIXME).

        Returns:
            List: original search results
        """
        if f'{HANA3D_NAME}_search_results_orig' not in self.context.window_manager:
            return []
        return self.context.window_manager[f'{HANA3D_NAME}_search_results_orig']

    @results.setter  # noqa : WPS110
    def results(self, results_value: List[SearchResult]):  # noqa : WPS110
        self.context.window_manager[f'{HANA3D_NAME}_search_results'] = results_value

    @results_orig.setter
    def results_orig(self, results_orig_value: List[SearchResult]):
        self.context.window_manager[f'{HANA3D_NAME}_search_results_orig'] = results_orig_value
