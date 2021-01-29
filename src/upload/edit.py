"""Edit assets module."""

import bpy
from bpy.props import BoolProperty, EnumProperty

from ... import hana3d_types, paths, render, utils
from ...config import HANA3D_DESCRIPTION, HANA3D_NAME
from ..async_loop.async_mixin import AsyncModalOperatorMixin

HANA3D_EXPORT_DATA_FILE = f'{HANA3D_NAME}_data.json'


class EditAssetOperator(AsyncModalOperatorMixin, bpy.types.Operator):  # noqa: WPS214
    """Hana3D edit asset operator."""

    bl_idname = f'object.{HANA3D_NAME}_edit'
    bl_description = f'Edit asset in {HANA3D_DESCRIPTION}'

    bl_label = f'{HANA3D_DESCRIPTION} asset edit'
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
        ui.add_report(text='Preparing upload')

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
            ui.add_report(text='Upload finished successfully')
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

        try:
            await create_blend_file(props, ui, datafile, clean_file_path, filename)
        except Exception as error:
            logging.error(error)
            ui.add_report(text='Failed to create blend file')
            props.uploading = False
            return {'CANCELLED'}

        files = self._get_files_info(upload_set, export_data, tempdir, filename)

        for file_info in files:
            upload = await get_upload_url(props, ui, correlation_id, upload_data, file_info)
            uploaded = await upload_file(ui, file_info, upload['s3UploadUrl'])
            if uploaded:
                skip_post_process = self._check_uv_layers(ui, export_data)
                await confirm_upload(props, ui, correlation_id, upload['id'], skip_post_process)
            else:
                ui.add_report(text='Failed to send file')
                props.uploading = False
                return {'CANCELLED'}

        if props.remote_thumbnail:
            self._start_remote_thumbnail(props)

        if 'MAINFILE' in upload_set:
            await finish_asset_creation(props, ui, correlation_id, upload_data['id'])

        props.view_workspace = workspace
        props.uploading = False
        ui.add_report(text='Upload finished successfully')

        return {'FINISHED'}


class DeleteAssetOperator(AsyncModalOperatorMixin, bpy.types.Operator):  # noqa: WPS214
    """Hana3D edit asset operator."""

    bl_idname = f'object.{HANA3D_NAME}_delete'
    bl_description = f'Delete asset in {HANA3D_DESCRIPTION}'

    bl_label = f'{HANA3D_DESCRIPTION} asset delete'
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
        ui.add_report(text='Preparing upload')

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
            ui.add_report(text='Upload finished successfully')
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

        try:
            await create_blend_file(props, ui, datafile, clean_file_path, filename)
        except Exception as error:
            logging.error(error)
            ui.add_report(text='Failed to create blend file')
            props.uploading = False
            return {'CANCELLED'}

        files = self._get_files_info(upload_set, export_data, tempdir, filename)

        for file_info in files:
            upload = await get_upload_url(props, ui, correlation_id, upload_data, file_info)
            uploaded = await upload_file(ui, file_info, upload['s3UploadUrl'])
            if uploaded:
                skip_post_process = self._check_uv_layers(ui, export_data)
                await confirm_upload(props, ui, correlation_id, upload['id'], skip_post_process)
            else:
                ui.add_report(text='Failed to send file')
                props.uploading = False
                return {'CANCELLED'}

        if props.remote_thumbnail:
            self._start_remote_thumbnail(props)

        if 'MAINFILE' in upload_set:
            await finish_asset_creation(props, ui, correlation_id, upload_data['id'])

        props.view_workspace = workspace
        props.uploading = False
        ui.add_report(text='Upload finished successfully')

        return {'FINISHED'}


classes = (
    EditAssetOperator,
    DeleteAssetOperator,
)


def register():
    """Upload register."""
    for class_ in classes:
        bpy.utils.register_class(class_)


def unregister():
    """Upload unregister."""
    for class_ in reversed(classes):
        bpy.utils.unregister_class(class_)
