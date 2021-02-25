"""Edit assets operators."""
import uuid

import bpy

from .async_functions import delete_asset, edit_asset, edit_view
from .edit import get_edit_props
from .export_data import get_edit_data
from ..async_loop.async_mixin import AsyncModalOperatorMixin
from ..search import search
from ..ui.main import UI
from ...config import HANA3D_DESCRIPTION, HANA3D_NAME

HANA3D_EXPORT_DATA_FILE = f'{HANA3D_NAME}_data.json'


class EditAssetOperator(AsyncModalOperatorMixin, bpy.types.Operator):  # noqa: WPS214
    """Hana3D edit asset operator."""

    bl_idname = f'object.{HANA3D_NAME}_edit'
    bl_description = f'Edit asset in {HANA3D_DESCRIPTION}'

    bl_label = f'{HANA3D_DESCRIPTION} asset edit'
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    async def async_execute(self, context):
        """Edit asset async execute.

        Parameters:
            context: Blender context

        Returns:
            enum set in {‘RUNNING_MODAL’, ‘CANCELLED’, ‘FINISHED’, ‘PASS_THROUGH’, ‘INTERFACE’}
        """
        ui = UI()
        ui.add_report(text='Editing asset')

        correlation_id = str(uuid.uuid4())

        props = get_edit_props()
        asset_data, view_data = get_edit_data(props)

        await edit_asset(ui, correlation_id, props.id, asset_data)
        await edit_view(ui, correlation_id, props.view_id, view_data)

        search.run_operator()

        ui.add_report(text='Asset successfully edited')

        return {'FINISHED'}


class DeleteAssetOperator(AsyncModalOperatorMixin, bpy.types.Operator):  # noqa: WPS214
    """Hana3D edit asset operator."""

    bl_idname = f'object.{HANA3D_NAME}_delete'
    bl_description = f'Delete asset in {HANA3D_DESCRIPTION}'

    bl_label = f'{HANA3D_DESCRIPTION} asset delete'
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    async def async_execute(self, context):
        """Delete asset async execute.

        Parameters:
            context: Blender context

        Returns:
            enum set in {‘RUNNING_MODAL’, ‘CANCELLED’, ‘FINISHED’, ‘PASS_THROUGH’, ‘INTERFACE’}
        """
        ui = UI()
        ui.add_report(text='Deleting asset')

        props = get_edit_props()
        await delete_asset(ui, props.id)

        search.run_operator()

        ui.add_report(text='Asset deleted')

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
