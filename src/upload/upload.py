"""Upload."""
from dataclasses import dataclass
from typing import List

from bpy.types import Context

from ...config import (
    HANA3D_MATERIALS,
    HANA3D_MODELS,
    HANA3D_NAME,
    HANA3D_SCENES,
    HANA3D_UI,
)
from ..asset.asset_type import AssetType


class Upload(object):
    """Hana3D search information."""

    def __init__(self, context: Context, asset_type: AssetType = None):
        """Create a Search object.

        Args:
            context: Blender context.
            asset_type: Asset Type
        """
        self.context = context
        self.asset_type = asset_type if asset_type else self._get_asset_type_from_ui()

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
    def props(self):
        """Get search props.

        Returns:
            Any | None: search props if available
        """
        if self.asset_type == 'model' and hasattr(self.context.window_manager, HANA3D_MODELS):  # noqa : WPS421
            return getattr(self.context.window_manager, HANA3D_MODELS)
        elif self.asset_type == 'scene' and hasattr(self.context.window_manager, HANA3D_SCENES):  # noqa : WPS421
            return getattr(self.context.window_manager, HANA3D_SCENES)
        elif self.asset_type == 'material' and hasattr(self.context.window_manager, HANA3D_MATERIALS):  # noqa : WPS421
            return getattr(self.context.window_manager, HANA3D_MATERIALS)

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

    def _get_asset_type_from_ui(self) -> AssetType:
        uiprops = getattr(self.context.window_manager, HANA3D_UI)
        return uiprops.asset_type.lower()
