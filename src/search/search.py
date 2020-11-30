"""Search."""

from dataclasses import dataclass
from typing import List

from ...config import HANA3D_NAME


class Search(object):
    """Hana3D search information."""

    def __init__(self, context):
        """Create a Search object.

        Args:
            context: Blender context.
        """
        self.context = context

    @property  # noqa : WPS110
    def results(self) -> List:  # noqa : WPS110
        """Get search results.

        Returns:
            List: search results
        """
        if f'{HANA3D_NAME}_search_results' not in self.context.window_manager:
            return []
        return self.context.window_manager[f'{HANA3D_NAME}_search_results']

    @property
    def results_orig(self) -> List:
        """Get original search results (FIXME).

        Returns:
            List: original search results
        """
        if f'{HANA3D_NAME}_search_results_orig' not in self.context.window_manager:
            return []
        return self.context.window_manager[f'{HANA3D_NAME}_search_results_orig']

    @results.setter  # noqa : WPS110
    def results(self, results_value: List):  # noqa : WPS110
        self.context.window_manager[f'{HANA3D_NAME}_search_results'] = results_value

    @results_orig.setter
    def results_orig(self, results_orig_value: List):
        self.context.window_manager[f'{HANA3D_NAME}_search_results_orig'] = results_orig_value

    def results_by_asset_type(self, asset_type) -> List:
        """Get search results by asset_type.

        Args:
            asset_type: model | material | scene

        Returns:
            List: search results by asset type
        """
        return self.context.window_manager.get(f'{HANA3D_NAME}_{asset_type}_search')

    def results_orig_by_asset_type(self, asset_type) -> List:
        """Get search results by asset_type.

        Args:
            asset_type: model | material | scene

        Returns:
            List: search results by asset type
        """
        return self.context.window_manager.get(f'{HANA3D_NAME}_{asset_type}_search_orig')


@dataclass
class SearchResult(object):
    """Hana3D search result."""

    todo: str
