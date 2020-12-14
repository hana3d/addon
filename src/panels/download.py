"""Download panel."""
from bpy.types import Panel

from ... import download
from ...config import HANA3D_DESCRIPTION, HANA3D_NAME


class Hana3dDownloadPanel(Panel):
    """Download panel."""

    bl_category = HANA3D_DESCRIPTION
    bl_idname = f'VIEW3D_PT_{HANA3D_NAME}_downloads'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_label = f'Downloads {HANA3D_DESCRIPTION}'

    @classmethod
    def poll(cls, context):  # noqa: D102
        return len(download.download_threads) > 0  # noqa: WPS507

    def draw(self, context):  # noqa: D102
        layout = self.layout
        for view_id, thread in download.download_threads.items():
            row = layout.row()
            row.label(text=thread.asset_data['name'])
            row.label(text=f'{int(thread.tcom.progress)}%')
            op = row.operator(f'scene.{HANA3D_NAME}_download_kill', text='', icon='CANCEL')
            op.view_id = view_id
