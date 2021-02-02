"""Send logs operator."""
import uuid

import bpy

from .async_functions import send_logs
from .logger import get_log_file
from ..async_loop.async_mixin import AsyncModalOperatorMixin
from ..ui.main import UI
from ...config import HANA3D_DESCRIPTION, HANA3D_NAME


class SendLogsOperator(AsyncModalOperatorMixin, bpy.types.Operator):  # noqa: WPS214
    """Hana3D send logs operator."""

    bl_idname = f'wm.{HANA3D_NAME}_logs'
    bl_description = f'Send logs to {HANA3D_DESCRIPTION}'

    bl_label = f'{HANA3D_DESCRIPTION} send logs'
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    async def async_execute(self, context):
        """Send logs async execute.
        Parameters:
            context: Blender context
        Returns:
            enum set in {‘RUNNING_MODAL’, ‘CANCELLED’, ‘FINISHED’, ‘PASS_THROUGH’, ‘INTERFACE’}
        """
        ui = UI()
        ui.add_report(text='Sending logs')

        correlation_id = str(uuid.uuid4())
        props = getattr(context.window_manager, HANA3D_NAME)
        log_file = get_log_file()

        await send_logs(ui, correlation_id, props.issue_key, log_file)

        ui.add_report(text='Logs sent')

        return {'FINISHED'}

classes = (
    SendLogsOperator,
)


def register():
    """Send logs register."""
    for class_ in classes:
        bpy.utils.register_class(class_)


def unregister():
    """Send logs unregister."""
    for class_ in reversed(classes):
        bpy.utils.unregister_class(class_)
