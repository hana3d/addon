"""Upload assets module."""

import json
import os
import pathlib
import tempfile
import uuid
from typing import List, Union

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
from .export_data import get_export_data
from .upload import get_upload_props
from ..async_loop.async_mixin import AsyncModalOperatorMixin
from ..ui.main import UI
from ... import hana3d_types, paths, render, utils
from ...config import HANA3D_DESCRIPTION, HANA3D_NAME

HANA3D_EXPORT_DATA_FILE = f'{HANA3D_NAME}_data.json'


asset_types = (
    ('MODEL', 'Model', 'set of objects'),
    ('SCENE', 'Scene', 'scene'),
    ('MATERIAL', 'Material', 'any .blend Material'),
    ('ADDON', 'Addon', 'addon'),
)


class UploadAssetOperator(AsyncModalOperatorMixin, bpy.types.Operator):  # noqa: WPS214
    """Hana3D upload asset operator."""

    bl_idname = f'object.{HANA3D_NAME}_upload'
    bl_description = f'Upload or re-upload asset + thumbnail + metadata to {HANA3D_DESCRIPTION}'

    bl_label = f'{HANA3D_DESCRIPTION} asset upload'
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    # type of upload - model, material, textures, e.t.c.
    asset_type: EnumProperty(   # type: ignore
        name='Type',
        items=asset_types,
        description='Type of upload',
        default='MODEL',
    )

    reupload: BoolProperty(  # type: ignore
        name='reupload',
        description='reupload but also draw so that it asks what to reupload',
        default=False,
        options={'SKIP_SAVE'},
    )

    metadata: BoolProperty(name='metadata', default=True, options={'SKIP_SAVE'})    # type: ignore

    thumbnail: BoolProperty(name='thumbnail', default=False, options={'SKIP_SAVE'})  # type: ignore

    main_file: BoolProperty(name='main file', default=False, options={'SKIP_SAVE'})  # type: ignore

    @classmethod
    def poll(cls, context):
        """Upload poll.

        Parameters:
            context: Blender context

        Returns:
            bool: if there is a active object and if it is not already uploading
        """
        props = get_upload_props()
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

        props, workspace, correlation_id, basename, ext, tempdir = self._get_basic_data()
        props.uploading = True

        upload_set = ['METADATA', 'MAINFILE']
        self._update_props(props, upload_set)

        export_data, upload_data = get_export_data(props)

        self._thumbnail_check(props, ui, upload_set, export_data)

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
        filename = f'{upload_data["viewId"]}.blend'

        source_filepath = self._save_blend_file(tempdir, ext)
        clean_file_path = paths.get_clean_filepath()
        datafile = self._write_json_file(
            tempdir,
            source_filepath,
            clean_file_path,
            export_data,
            upload_data,
            upload_set,
            correlation_id,
        )

        await create_blend_file(props, ui, datafile, clean_file_path, filename)

        files = self._get_files_info(upload_set, export_data, tempdir, filename)

        for file_info in files:
            upload = await get_upload_url(props, ui, correlation_id, upload_data, file_info)
            uploaded = await upload_file(ui, file_info, upload['s3UploadUrl'])
            if uploaded:
                skip_post_process = self._check_uv_layers(ui)
                await confirm_upload(props, ui, correlation_id, upload['id'], skip_post_process)
            else:
                ui.add_report(text='failed to send file')
                props.uploading = False
                return {'CANCELLED'}

        if props.remote_thumbnail:
            self._start_remote_thumbnail(props)

        if 'MAINFILE' in upload_set:
            await finish_asset_creation(props, ui, correlation_id, upload_data['id'])

        props.view_workspace = workspace
        props.uploading = False
        ui.add_report(text='upload finished successfully')

        return {'FINISHED'}

    def _get_basic_data(self):  # noqa: WPS210
        active_asset = utils.get_active_asset()

        if self.asset_type == 'MODEL':
            utils.fill_object_metadata(active_asset)

        props = getattr(active_asset, HANA3D_NAME)
        workspace = props.workspace
        correlation_id = str(uuid.uuid4())

        basename, ext = os.path.splitext(bpy.data.filepath)
        if not ext:
            ext = '.blend'
        tempdir = tempfile.mkdtemp()
        return props, workspace, correlation_id, basename, ext, tempdir

    def _update_props(self, props: hana3d_types.Props, upload_set: List[str]):
        utils.name_update()

        if not self.reupload:
            props.view_id = ''
            props.id = ''   # noqa: WPS125

        if 'jobs' not in props.render_data:
            props.render_data['jobs'] = []

        if props.has_thumbnail:
            upload_set.append('THUMBNAIL')
            props.remote_thumbnail = False
        else:
            props.remote_thumbnail = True

    def _thumbnail_check(
        self,
        props: hana3d_types.Props,
        ui: UI,
        upload_set: List[str],
        export_data: dict,
    ):
        if 'THUMBNAIL' in upload_set and not os.path.exists(export_data['thumbnail_path']):
            ui.add_report(text='Thumbnail not found')
            props.uploading = False
            return {'CANCELLED'}

    def _save_blend_file(self, tempdir: Union[str, pathlib.Path], ext: str) -> str:
        source_filepath = os.path.join(tempdir, f'export_hana3d{ext}')
        autopack = bpy.data.use_autopack is True
        if autopack:
            bpy.ops.file.autopack_toggle()
        bpy.ops.wm.save_as_mainfile(filepath=source_filepath, compress=False, copy=True)
        if autopack:
            bpy.ops.file.autopack_toggle()

        return source_filepath

    def _write_json_file(   # noqa: WPS211
        self,
        tempdir: str,
        source_filepath: Union[str, pathlib.Path],
        clean_file_path: Union[str, pathlib.Path],
        export_data: dict,
        upload_data: dict,
        upload_set: List[str],
        correlation_id: str,
    ):
        datafile = os.path.join(tempdir, HANA3D_EXPORT_DATA_FILE)
        json_data = {
            'clean_file_path': clean_file_path,
            'source_filepath': source_filepath,
            'temp_dir': tempdir,
            'export_data': export_data,
            'upload_data': upload_data,
            'upload_set': upload_set,
            'correlation_id': correlation_id,
        }

        with open(datafile, 'w') as opened_file:
            json.dump(json_data, opened_file)

        return datafile

    def _check_uv_layers(self, ui: UI) -> str:
        skip_post_process = 'false'
        multiple_uv_meshes = [mesh.name for mesh in bpy.data.meshes if len(mesh.uv_layers) > 1]
        if multiple_uv_meshes:
            ui.add_report(
                'GLB and USDZ will not be generated: at least 1 mesh has more than 1 UV Map',
            )
            ui.add_report(f'Meshes with more than 1 UV Map: {", ".join(multiple_uv_meshes)}')
            skip_post_process = 'true'

        return skip_post_process

    def _get_files_info(
        self,
        upload_set: List[str],
        export_data: dict,
        tempdir: str,
        filename: str,
    ):
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
                    'file_path': os.path.join(tempdir, filename),
                    'publish_message': export_data['publish_message'],
                },
            )
        return files

    def _start_remote_thumbnail(self, props: hana3d_types.Props):
        thread = render.RenderThread(
            props,
            engine='CYCLES',
            frame_start=1,
            frame_end=1,
            is_thumbnail=True,
        )
        thread.start()
        render.render_threads.append(thread)


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
