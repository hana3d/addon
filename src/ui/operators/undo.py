"""Undo With Context Operator."""
from typing import Set

import bpy

from ....config import HANA3D_DESCRIPTION, HANA3D_NAME
from ....report_tools import execute_wrapper
from ..main import UI


class UndoWithContext(bpy.types.Operator):
    """Regenerate cobweb."""

    bl_idname = f'wm.{HANA3D_NAME}_undo_push_context'
    bl_label = f'{HANA3D_DESCRIPTION} undo push'
    bl_description = f'{HANA3D_DESCRIPTION} undo push with fixed context'
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    message: bpy.props.StringProperty(   # type: ignore
        'Undo Message',
        default=f'{HANA3D_DESCRIPTION} operation',
    )

    @execute_wrapper
    def execute(self, context: bpy.types.Context) -> Set[str]:  # noqa: D102
        c_dict = bpy.context.copy()
        c_dict.update(region='WINDOW')
        if context.area is None or context.area.type != 'VIEW_3D':
            window, area, region = UI().get_largest_view3d()
            override = {'window': window, 'screen': window.screen, 'area': area, 'region': region}
            c_dict.update(override)
        bpy.ops.ed.undo_push(c_dict, 'INVOKE_REGION_WIN', message=self.message)
        return {'FINISHED'}
