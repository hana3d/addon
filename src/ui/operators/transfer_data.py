"""Transfer Hana3D Data Operator."""
from typing import Set

import bpy

from ....config import HANA3D_DESCRIPTION, HANA3D_NAME
from ....report_tools import execute_wrapper


class TransferHana3DData(bpy.types.Operator):
    """Regenerate cobweb."""

    bl_idname = f'object.{HANA3D_NAME}_data_transfer'
    bl_label = f'Transfer {HANA3D_DESCRIPTION} data'
    bl_description = (
        'Transfer hana3d metadata from one object to another when fixing uploads'
        + ' with wrong parenting.'
    )
    bl_options = {'REGISTER', 'UNDO'}

    @execute_wrapper
    def execute(self, context: bpy.types.Context) -> Set[str]:  # noqa: D102
        source_ob = bpy.context.active_object
        for target_ob in bpy.context.selected_objects:
            if target_ob != source_ob:
                target_ob.property_unset(HANA3D_NAME)
                for key in source_ob.keys():
                    target_ob[key] = source_ob[key]
        source_ob.property_unset(HANA3D_NAME)
        return {'FINISHED'}
