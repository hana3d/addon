"""Panel to demo popup notice and ignoring functionality."""
from bpy.types import Panel

from ... import addon_updater_ops
from ...config import HANA3D_DESCRIPTION, HANA3D_NAME


class Hana3DUpdaterPanel(Panel):
    """Panel to demo popup notice and ignoring functionality."""

    bl_label = 'Preferences'
    bl_idname = f'VIEW3D_PT_{HANA3D_NAME}_UpdaterPanel'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_context = 'objectmode'
    bl_category = HANA3D_DESCRIPTION

    def draw(self, context):  # noqa: D102
        layout = self.layout

        mainrow = layout.row()
        col = mainrow.column()
        addon_updater_ops.update_settings_ui_condensed(self, context, col)

        addon_updater_ops.check_for_update_background()
        addon_updater_ops.update_notice_box_ui(self, context)

        layout.prop(context.preferences.addons[HANA3D_NAME].preferences, 'search_in_header')
