from bpy.types import Panel

from ..preferences.preferences import Preferences
from ...config import HANA3D_DESCRIPTION, HANA3D_NAME


class Hana3DLogin(Panel):
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
        layout = self.layout
        user_preferences = Preferences().get()

        if user_preferences.login_attempt:
            self._draw_login_progress()
            return

        self._draw_login_buttons()

    def _draw_login_progress(self):
        layout = self.layout

        layout.label(text='Login through browser')
        layout.label(text='in progress.')
        layout.operator(f'wm.{HANA3D_NAME}_login_cancel', text='Cancel', icon='CANCEL')

    def _draw_login_buttons(self):
        user_preferences = Preferences().get()

        if user_preferences.login_attempt:
            self._draw_login_progress()
        else:
            layout = self.layout
            if user_preferences.api_key == '':
                layout.operator(f'wm.{HANA3D_NAME}_login', text='Login / Sign up', icon='URL')
            else:
                layout.operator(f'wm.{HANA3D_NAME}_logout', text='Logout', icon='URL')
