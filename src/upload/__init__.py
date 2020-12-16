"""Upload assets module."""

import json
import os
import tempfile
import uuid

import bpy
from bpy.props import BoolProperty, EnumProperty

from .async_functions import (
    confirm_upload,
    create_asset,
    create_blend_file,
    finish_asset_creation,
    get_upload_url,
    upload_file,
)
from .data_helper import get_export_data
from ..async_loop.async_mixin import AsyncModalOperatorMixin
from ..ui.main import UI
from ... import paths, render, utils
from ...config import HANA3D_DESCRIPTION, HANA3D_NAME

HANA3D_EXPORT_DATA_FILE = f'{HANA3D_NAME}_data.json'


asset_types = (
    ('MODEL', 'Model', 'set of objects'),
    ('SCENE', 'Scene', 'scene'),
    ('MATERIAL', 'Material', 'any .blend Material'),
    ('ADDON', 'Addon', 'addon'),
)


class UploadAssetOperator(AsyncModalOperatorMixin, bpy.types.Operator):
    """Hana3D upload asset operator."""

    bl_idname = f'object.{HANA3D_NAME}_upload'
    bl_description = f'Upload or re-upload asset + thumbnail + metadata to {HANA3D_DESCRIPTION}'

    bl_label = 'hana3d asset upload'
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    # type of upload - model, material, textures, e.t.c.
    asset_type: EnumProperty(
        name='Type',
        items=asset_types,
        description='Type of upload',
        default='MODEL',
    )

    reupload: BoolProperty(
        name='reupload',
        description='reupload but also draw so that it asks what to reupload',
        default=False,
        options={'SKIP_SAVE'},
    )

    metadata: BoolProperty(name='metadata', default=True, options={'SKIP_SAVE'})

    thumbnail: BoolProperty(name='thumbnail', default=False, options={'SKIP_SAVE'})

    main_file: BoolProperty(name='main file', default=False, options={'SKIP_SAVE'})

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

    async def async_execute(self, context):  # noqa: WPS217,WPS210
        """Upload async execute.

        Parameters:
            context: Blender context

        Returns:
            enum set in {‘RUNNING_MODAL’, ‘CANCELLED’, ‘FINISHED’, ‘PASS_THROUGH’, ‘INTERFACE’}
        """
        ui = UI()
        ui.add_report(text='preparing upload')

        active_asset = utils.get_active_asset()
        props = getattr(active_asset, HANA3D_NAME)

        workspace = props.workspace

        correlation_id = str(uuid.uuid4())

        basename, ext = os.path.splitext(bpy.data.filepath)
        if not ext:
            ext = '.blend'

        utils.name_update()

        if not self.reupload:
            props.view_id = ''
            props.id = ''   # noqa: WPS125

        if 'jobs' not in props.render_data:
            props.render_data['jobs'] = []

        if self.asset_type == 'MODEL':
            utils.fill_object_metadata(active_asset)

        upload_set = ['METADATA', 'MAINFILE']
        if props.has_thumbnail:
            upload_set.append('THUMBNAIL')
            props.remote_thumbnail = False
        else:
            props.remote_thumbnail = True

        export_data, upload_data = get_export_data(props)

        if 'THUMBNAIL' in upload_set and not os.path.exists(export_data['thumbnail_path']):
            ui.add_report(text='Thumbnail not found')
            props.uploading = False
            return {'CANCELLED'}

        asset_id = await create_asset(props, ui, props.id, upload_data, correlation_id)
        props.id = asset_id  # noqa: WPS125

        if upload_set == ['METADATA']:
            props.uploading = False
            ui.add_report(text='upload finished successfully')
            props.view_workspace = workspace
            return {'FINISHED'}

        if self.reupload:
            upload_data['id_parent'] = props.view_id
        props.view_id = str(uuid.uuid4())
        upload_data['viewId'] = props.view_id
        upload_data['id'] = props.id

        tempdir = tempfile.mkdtemp()
        datafile = os.path.join(tempdir, HANA3D_EXPORT_DATA_FILE)
        source_filepath = os.path.join(tempdir, f'export_hana3d{ext}')
        clean_file_path = paths.get_clean_filepath()
        json_data = {
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

        with open(datafile, 'w') as opened_file:
            json.dump(json_data, opened_file)

        filename = f'{upload_data["viewId"]}.blend'
        await create_blend_file(props, ui, datafile, clean_file_path, filename)

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
                },
            )
        if 'MAINFILE' in upload_set:
            files.append(
                {
                    'type': 'blend',
                    'index': 0,
                    'file_path': os.path.join(data['temp_dir'], filename),
                    'publish_message': export_data['publish_message'],
                },
            )

        for file_info in files:
            upload = await get_upload_url(props, ui, correlation_id, upload_data, file_info)
            uploaded = await upload_file(ui, file_info, upload['s3UploadUrl'])
            if uploaded:
                await confirm_upload(props, ui, correlation_id, upload['id'], skip_post_process)
            else:
                ui.add_report(text='failed to send file')
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
            await finish_asset_creation(props, ui, correlation_id, upload_data['id'])

        props.uploading = False
        ui.add_report(text='upload finished successfully')

        return {'FINISHED'}


classes = (
    UploadAssetOperator,
)


def register():
    """Upload register."""
    for class_ in classes:
        bpy.utils.register_class(class_)


def unregister():
    """Upload unregister."""
    for class_ in reversed(classes):
        bpy.utils.unregister_class(class_)
