"""Auxiliary data manipulation functions."""
import bpy

from ..libraries.libraries import get_libraries
from ..tags.tags import get_tags
from ..unified_props import Unified
from ... import hana3d_types, utils


def get_export_data(props: hana3d_types.UploadProps):  # noqa: WPS210
    """Get required data from Blender for upload.

    Arguments:
        props: Hana3D upload props

    Returns:
        export_data, upload_data

    Raises:
        Exception: Unexpected asset_type
    """
    unified_props = Unified(bpy.context).props
    export_data = {
        'type': props.asset_type,
        'thumbnail_path': bpy.path.abspath(props.thumbnail),
    }

    if props.asset_type.upper() == 'MODEL':
        upload_data, upload_params = _get_model_data(export_data, props)

    elif props.asset_type.upper() == 'SCENE':
        upload_data, upload_params = _get_scene_data(export_data)

    elif props.asset_type.upper() == 'MATERIAL':
        upload_data, upload_params = _get_material_data(export_data)

    else:
        raise Exception(f'Unexpected asset_type={props.asset_type}')

    upload_data['name'] = props.name
    upload_data['description'] = props.description
    upload_data['parameters'] = upload_params
    upload_data['parameters'] = utils.dict_to_params(upload_data['parameters'])
    upload_data['is_public'] = props.is_public
    if unified_props.workspace != '' and not props.is_public:
        upload_data['workspace'] = unified_props.workspace

    metadata: dict = {}
    if metadata:
        upload_data['metadata'] = metadata

    upload_data['tags'] = get_tags(props)
    upload_data['libraries'] = get_libraries(props)

    export_data['publish_message'] = props.publish_message

    return export_data, upload_data


def _get_model_data(export_data: dict, props: hana3d_types.UploadProps):  # noqa: WPS210
    mainmodel = utils.get_active_model(bpy.context)

    obs = utils.get_hierarchy(mainmodel)
    obnames = [ob.name for ob in obs]
    export_data['type'] = 'MODEL'
    export_data['models'] = obnames

    upload_data = {
        'assetType': 'model',
    }
    upload_params = {
        'dimensionX': round(props.dimensions[0], 4),
        'dimensionY': round(props.dimensions[1], 4),
        'dimensionZ': round(props.dimensions[2], 4),
        'boundBoxMinX': round(props.bbox_min[0], 4),
        'boundBoxMinY': round(props.bbox_min[1], 4),
        'boundBoxMinZ': round(props.bbox_min[2], 4),
        'boundBoxMaxX': round(props.bbox_max[0], 4),
        'boundBoxMaxY': round(props.bbox_max[1], 4),
        'boundBoxMaxZ': round(props.bbox_max[2], 4),
        'faceCount': props.face_count,
        'faceCountRender': props.face_count_render,
        'objectCount': props.object_count,
    }

    return upload_data, upload_params


def _get_material_data(export_data: dict):
    mat = bpy.context.active_object.active_material

    export_data['type'] = 'MATERIAL'
    export_data['material'] = str(mat.name)

    upload_data = {
        'assetType': 'material',
    }

    upload_params: dict = {}

    return upload_data, upload_params


def _get_scene_data(export_data: dict):
    name = bpy.context.scene.name

    export_data['type'] = 'SCENE'
    export_data['scene'] = name

    upload_data = {
        'assetType': 'scene',
    }

    upload_params: dict = {}

    return upload_data, upload_params
