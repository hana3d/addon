"""Run Asset Bar With Context Operator."""
from typing import Set

import bpy

from ..main import UI
from ....config import HANA3D_DESCRIPTION, HANA3D_NAME
from ....report_tools import execute_wrapper


class RunAssetBarWithContext(bpy.types.Operator):
    """Regenerate cobweb."""

    bl_idname = f'object.{HANA3D_NAME}_run_assetbar_fix_context'
    bl_label = f'{HANA3D_DESCRIPTION} assetbar with fixed context'
    bl_description = 'Run assetbar with fixed context'
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    @execute_wrapper  # noqa: WPS210
    def execute(self, context: bpy.types.Context) -> Set[str]:  # noqa: WPS210,D102
        c_dict = bpy.context.copy()
        c_dict.update(region='WINDOW')
        if context.area is None or context.area.type != 'VIEW_3D':
            window, area, region = UI().get_largest_view3d()
            override = {'window': window, 'screen': window.screen, 'area': area, 'region': region}
            c_dict.update(override)
        asset_bar_op = getattr(bpy.ops.view3d, f'{HANA3D_NAME}_asset_bar')
        asset_bar_op(
            c_dict,
            'INVOKE_REGION_WIN',
            keep_running=True,
            do_search=False,
        )
        return {'FINISHED'}
