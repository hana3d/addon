"""Send logs Panel."""

from bpy.types import Panel

from ...config import HANA3D_DESCRIPTION, HANA3D_NAME

JIRA_PROJECT = 'HANA3DESK'


class Hana3DSendLogsPanel(Panel):  # noqa: WPS214
    """Send logs Panel."""

    bl_category = HANA3D_DESCRIPTION
    bl_idname = f'VIEW3D_PT_{HANA3D_NAME}_logs'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_label = f'{HANA3D_DESCRIPTION} Support'

    @classmethod
    def poll(cls, context):  # noqa: D102
        return True

    def draw(self, context):  # noqa: D102,WPS210,WPS213
        layout = self.layout

        props = getattr(context.window_manager, HANA3D_NAME)
        box = layout.box()
        box.label(text='Send logs after ticket creation', icon='CONSOLE')
        row = box.row()
        row.label(text=f'{JIRA_PROJECT}-')
        row.alert = (props.issue_key == '' or not self._is_number(props.issue_key))
        row.prop(props, 'issue_key', text='')
        box.operator(f'wm.{HANA3D_NAME}_logs', text='Send logs', icon='TEXT')

    def _is_number(self, text: str) -> bool:
        try:
            int(text)
            return True
        except ValueError:
            return False
