"""Login panel."""
from bpy.types import Panel

from .lib import draw_login_buttons, draw_login_progress
from ..preferences.preferences import Preferences
from ...config import HANA3D_DESCRIPTION, HANA3D_NAME


class Hana3DLoginPanel(Panel):
    """Login panel."""

    bl_category = HANA3D_DESCRIPTION
    bl_idname = f'VIEW3D_PT_{HANA3D_NAME}_login'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_label = f'{HANA3D_DESCRIPTION} Login'
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):  # noqa: D102
        return True

    def draw(self, context):  # noqa: D102
        user_preferences = Preferences().get()

        if user_preferences.login_attempt:
            draw_login_progress(self.layout)
            return

        draw_login_buttons(self.layout)
