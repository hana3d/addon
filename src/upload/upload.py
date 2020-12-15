import bpy

from ... import utils
from ...config import HANA3D_NAME


def get_upload_props():
    active_asset = utils.get_active_asset()
    if active_asset is None:
        return None
    return getattr(active_asset, HANA3D_NAME)


def get_upload_props_by_view_id(asset_type: str, view_id: str):
    """Get upload props by view_id.

    Parameters:
        asset_type: str (model|scene|material)
        view_id: str
    """
    asset = None
    if asset_type == 'model':
        asset = utils.get_active_model(bpy.context, view_id)
    elif asset_type == 'scene':
        scenes = [
            ob
            for ob in bpy.data.scenes
            if getattr(ob, HANA3D_NAME) and getattr(ob, HANA3D_NAME).view_id == view_id
        ]
        asset = scenes[0]
    elif asset_type == 'material':
        materials = [
            ob
            for ob in bpy.data.materials
            if getattr(ob, HANA3D_NAME) and getattr(ob, HANA3D_NAME).view_id == view_id
        ]
        asset = materials[0]
    return getattr(asset, HANA3D_NAME)
