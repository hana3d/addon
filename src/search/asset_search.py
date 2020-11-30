"""Asset Search."""

from typing import List

from ...config import HANA3D_NAME


class AssetSearch(object):
    # TODO: merge this class with `Search`
    """Hana3D search information by asset type."""

    def __init__(self, context, asset_type):
        """Create a Search object by asset type.

        Args:
            context: Blender context.
            asset_type: model | material | scene
        """
        self.context = context
        # TODO remove inconsistency between e.g. `model` and `MODEL`
        self.asset_type = asset_type.lower()

    @property
    def results(self) -> List:  # noqa : WPS110
        """Get search results by asset type.

        Returns:
            List: search results by asset type
        """
        return self.context.window_manager.get(f'{HANA3D_NAME}_{self.asset_type}_search')

    @property
    def results_orig(self) -> List:
        """Get original search results by asset type (FIXME).

        Returns:
            List: original search results by asset type
        """
        return self.context.window_manager.get(f'{HANA3D_NAME}_{self.asset_type}_search_orig')

    @results.setter
    def results(self, results: List):  # noqa : WPS110
        self.context.window_manager[f'{HANA3D_NAME}_{self.asset_type}_search'] = results

    @results_orig.setter
    def results_orig(self, results_orig: List):
        self.context.window_manager[f'{HANA3D_NAME}_{self.asset_type}_search_orig'] = results_orig
