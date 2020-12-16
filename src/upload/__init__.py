"""Upload assets module."""

import json
import os
import tempfile
import uuid

import bpy
from bpy.props import BoolProperty, EnumProperty

from ... import hana3d_types, logger, paths, render, ui, utils
from ...config import HANA3D_DESCRIPTION, HANA3D_NAME
from ..async_loop.async_mixin import AsyncModalOperatorMixin
from .async_functions import (
    confirm_upload,
    create_asset,
    create_blend_file,
    finish_asset_creation,
    get_upload_url,
    upload_file,
)

HANA3D_EXPORT_DATA_FILE = HANA3D_NAME + "_data.json"


asset_types = (
    ('MODEL', 'Model', 'set of objects'),
    ('SCENE', 'Scene', 'scene'),
    ('MATERIAL', 'Material', 'any .blend Material'),
    ('ADDON', 'Addon', 'addon'),
)


def _get_export_data(
    props: hana3d_types.Props,
    path_computing: str = 'uploading',
    path_state: str = 'upload_state',
):
    export_data = {
        "type": props.asset_type,
        "thumbnail_path": bpy.path.abspath(props.thumbnail),
    }
    upload_params = {}
    if props.asset_type.upper() == 'MODEL':
        # Prepare to save the file
        mainmodel = utils.get_active_model(bpy.context)

        obs = utils.get_hierarchy(mainmodel)
        obnames = []
        for ob in obs:
            obnames.append(ob.name)
        export_data["type"] = 'MODEL'
        export_data["models"] = obnames

        eval_path = f"bpy.data.objects['{mainmodel.name}']"

        upload_data = {
            "assetType": 'model',
        }
        upload_params = {
            "dimensionX": round(props.dimensions[0], 4),
            "dimensionY": round(props.dimensions[1], 4),
            "dimensionZ": round(props.dimensions[2], 4),
            "boundBoxMinX": round(props.bbox_min[0], 4),
            "boundBoxMinY": round(props.bbox_min[1], 4),
            "boundBoxMinZ": round(props.bbox_min[2], 4),
            "boundBoxMaxX": round(props.bbox_max[0], 4),
            "boundBoxMaxY": round(props.bbox_max[1], 4),
            "boundBoxMaxZ": round(props.bbox_max[2], 4),
            "faceCount": props.face_count,
            "faceCountRender": props.face_count_render,
            "objectCount": props.object_count,
        }

    elif props.asset_type.upper() == 'SCENE':
        # Prepare to save the file
        name = bpy.context.scene.name

        export_data["type"] = 'SCENE'
        export_data["scene"] = name

        eval_path = f"bpy.data.scenes['{name}']"

        upload_data = {
            "assetType": 'scene',
        }
        upload_params = {
            # TODO add values
            # "faceCount": 1,  # props.face_count,
            # "faceCountRender": 1,  # props.face_count_render,
            # "objectCount": 1,  # props.object_count,
        }

    elif props.asset_type.upper() == 'MATERIAL':
        mat = bpy.context.active_object.active_material

        export_data["type"] = 'MATERIAL'
        export_data["material"] = str(mat.name)

        eval_path = f"bpy.data.materials['{mat.name}']"

        upload_data = {
            "assetType": 'material',
        }

        upload_params = {}
    else:
        raise Exception(f'Unexpected asset_type={props.asset_type}')

    bg_process_params = {
        'eval_path_computing': f'{eval_path}.{HANA3D_NAME}.{path_computing}',
        'eval_path_state': f'{eval_path}.{HANA3D_NAME}.{path_state}',
        'eval_path': eval_path,
    }

    upload_data["sourceAppName"] = "blender"
    upload_data["sourceAppVersion"] = '{}.{}.{}'.format(*utils.get_addon_version())
    upload_data["addonVersion"] = '{}.{}.{}'.format(*utils.get_addon_blender_version())

    upload_data["name"] = props.name
    upload_data["description"] = props.description

    upload_data['parameters'] = upload_params

    upload_data["is_public"] = props.is_public
    if props.workspace != '' and not props.is_public:
        upload_data['workspace'] = props.workspace

    metadata = {}
    if hasattr(props, 'custom_props'):
        metadata.update(props.custom_props)
    if metadata:
        upload_data['metadata'] = metadata

    upload_data['tags'] = []
    for tag in props.tags_list.keys():
        if props.tags_list[tag].selected is True:
            upload_data["tags"].append(tag)

    upload_data['libraries'] = []
    for library in props.libraries_list.keys():
        if props.libraries_list[library].selected is True:
            library_id = props.libraries_list[library].id_
            library = {}
            library.update({
                'id': library_id,
            })
            if props.custom_props.keys() != []:
                custom_props = {}
                for name in props.custom_props.keys():
                    value = props.custom_props[name]
                    slug = props.custom_props_info[name]['slug']
                    prop_library_id = props.custom_props_info[name]['library_id']
                    if prop_library_id == library_id:
                        custom_props.update({slug: value})
                library.update({'metadata': {'view_props': custom_props}})
            upload_data['libraries'].append(library)

    export_data['publish_message'] = props.publish_message

    return export_data, upload_data, bg_process_params


class UploadAssetOperator(AsyncModalOperatorMixin, bpy.types.Operator):
    """Hana3D upload asset operator."""

    bl_idname = f"object.{HANA3D_NAME}_upload"
    bl_description = f"Upload or re-upload asset + thumbnail + metadata to {HANA3D_DESCRIPTION}"

    bl_label = "hana3d asset upload"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    # type of upload - model, material, textures, e.t.c.
    asset_type: EnumProperty(
        name="Type",
        items=asset_types,
        description="Type of upload",
        default="MODEL",
    )

    reupload: BoolProperty(
        name="reupload",
        description="reupload but also draw so that it asks what to reupload",
        default=False,
        options={'SKIP_SAVE'},
    )

    metadata: BoolProperty(name="metadata", default=True, options={'SKIP_SAVE'})

    thumbnail: BoolProperty(name="thumbnail", default=False, options={'SKIP_SAVE'})

    main_file: BoolProperty(name="main file", default=False, options={'SKIP_SAVE'})

    @classmethod
    def poll(cls, context):
        """Upload poll.

        Parameters:
            context: Blender context

        Returns:
            bool: if there is a active object and if it is not already uploading
        """
        props = utils.get_upload_props()
        return bpy.context.view_layer.objects.active is not None and not props.uploading

    async def async_execute(self, context):
        """Upload async execute.

        Parameters:
            context: Blender context

        Returns:
            enum set in {‘RUNNING_MODAL’, ‘CANCELLED’, ‘FINISHED’, ‘PASS_THROUGH’, ‘INTERFACE’}
        """
        obj = utils.get_active_asset()
        props = getattr(obj, HANA3D_NAME)

        correlation_id = str(uuid.uuid4())

        if self.asset_type == 'MODEL':
            utils.fill_object_metadata(obj)

        upload_set = ['METADATA', 'MAINFILE']
        if props.has_thumbnail:
            upload_set.append('THUMBNAIL')
            props.remote_thumbnail = False
        else:
            props.remote_thumbnail = True

        utils.name_update()

        logger.show_report(props, text='preparing upload')

        if 'jobs' not in props.render_data:
            props.render_data['jobs'] = []

        if not self.reupload:
            props.view_id = ''
            props.id = ''
        export_data, upload_data, bg_process_params = _get_export_data(props)

        upload_data['parameters'] = utils.dict_to_params(upload_data['parameters'])

        basename, ext = os.path.splitext(bpy.data.filepath)
        if not ext:
            ext = ".blend"

        if 'THUMBNAIL' in upload_set and not os.path.exists(export_data["thumbnail_path"]):
            logger.show_report(props, text='Thumbnail not found')
            props.uploading = False
            return {'CANCELLED'}

        await create_asset(props, upload_data, correlation_id)

        workspace = props.workspace

        if upload_set == ['METADATA']:
            props.uploading = False
            logger.show_report(props, text='upload finished successfully')
            props.view_workspace = workspace
            return {'FINISHED'}

        if self.reupload:
            upload_data['id_parent'] = props.view_id
        props.view_id = str(uuid.uuid4())
        upload_data['viewId'] = props.view_id
        upload_data['id'] = props.id

        tempdir = tempfile.mkdtemp()
        datafile = os.path.join(tempdir, HANA3D_EXPORT_DATA_FILE)
        source_filepath = os.path.join(tempdir, "export_hana3d" + ext)
        clean_file_path = paths.get_clean_filepath()
        data = {
            'clean_file_path': clean_file_path,
            'source_filepath': source_filepath,
            'temp_dir': tempdir,
            'export_data': export_data,
            'upload_data': upload_data,
            'upload_set': upload_set,
            'correlation_id': correlation_id,
        }

        props.uploading = True
        autopack = bpy.data.use_autopack is True
        if autopack:
            bpy.ops.file.autopack_toggle()
        bpy.ops.wm.save_as_mainfile(filepath=source_filepath, compress=False, copy=True)

        with open(datafile, 'w') as s:
            json.dump(data, s)

        filename = f'{upload_data["viewId"]}.blend'
        await create_blend_file(props, datafile, clean_file_path, filename)

        skip_post_process = 'false'
        if any(len(mesh.uv_layers) > 1 for mesh in bpy.data.meshes):
            ui.add_report(
                'GLB and USDZ will not be generated: at least 1 mesh has more than 1 UV Map',
            )
            skip_post_process = 'true'

        files = []
        if 'THUMBNAIL' in upload_set:
            files.append(
                {
                    'type': 'thumbnail',
                    'index': 0,
                    'file_path': export_data['thumbnail_path'],
                    'publish_message': None,
                }
            )
        if 'MAINFILE' in upload_set:
            files.append(
                {
                    'type': 'blend',
                    'index': 0,
                    'file_path': os.path.join(data['temp_dir'], filename),
                    'publish_message': export_data['publish_message'],
                }
            )

        for file_ in files:
            upload = await get_upload_url(props, correlation_id, upload_data, file_)
            uploaded = await upload_file(props, file_, upload['s3UploadUrl'])
            if uploaded:
                await confirm_upload(props, correlation_id, upload['id'], skip_post_process)
            else:
                logger.show_report(props, text='failed to send file')
                props.uploading = False
                return {'CANCELLED'}

        if autopack:
            bpy.ops.file.autopack_toggle()

        if props.remote_thumbnail:
            thread = render.RenderThread(
                props,
                engine='CYCLES',
                frame_start=1,
                frame_end=1,
                is_thumbnail=True,
            )
            thread.start()
            render.render_threads.append(thread)

        props.view_workspace = workspace

        if 'MAINFILE' in upload_set:
            await finish_asset_creation(props, correlation_id, upload_data['id'])

        props.uploading = False
        logger.show_report(props, text='upload finished successfully')

        return {'FINISHED'}


classes = (
    UploadAssetOperator,
)


def register():
    """Upload register."""
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    """Upload unregister."""
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
