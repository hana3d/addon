"""Upload functions."""
import bpy

from ..asset.asset_type import AssetType
from ... import utils
from ...config import HANA3D_NAME


def get_upload_props():
    """Get upload props of the active asset.

    Returns:
        upload props
    """
    active_asset = utils.get_active_asset()
    if active_asset is None:
        return None
    return getattr(active_asset, HANA3D_NAME)


def get_upload_props_by_view_id(asset_type: AssetType, view_id: str):
    """Get upload props by view_id.

    Parameters:
        asset_type: AssetType
        view_id: str

    Returns:
        upload props
    """
    asset = None
    if asset_type == 'model':
        assets = bpy.context.blend_data.objects
    elif asset_type == 'scene':
        assets = bpy.data.scenes
    elif asset_type == 'material':
        assets = bpy.data.materials

    assets = [
        ob
        for ob in assets
        if getattr(ob, HANA3D_NAME) and getattr(ob, HANA3D_NAME).view_id == view_id
    ]
    asset = assets[0]
    return getattr(asset, HANA3D_NAME)
