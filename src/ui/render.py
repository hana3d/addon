"""Render UI."""
import bpy
from bpy.types import UIList

from ...config import HANA3D_NAME


class RENDER_UL_List(UIList): # noqa N801
    """List type to show all renders fo an asset."""
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname): # noqa WPS211,WPS110
        """Method called when drawing each item of a Blender UI List.

        Parameters:
            context: automatically passed
            layout: automatically passed
            data: automatically passed
            item: automatically passed
            icon: automatically passed
            active_data: automatically passed
            active_propname: automatically passed
        """
        show_image = layout.operator(f'{HANA3D_NAME}.show_image', icon='FULLSCREEN_ENTER')
        show_image.index = item.index

        layout.label(text=item.name, icon_value=item.icon_id)

        remove_render = layout.operator(f'{HANA3D_NAME}.remove_render', icon='CANCEL', text='')
        remove_render.job_id = item.job_id


classes = (
    RENDER_UL_List,
)

keymaps = []


def register():
    """Register."""
    for cl in classes:
        bpy.utils.register_class(cl)


def unregister():
    """Unregister."""
    for cl in reversed(classes):
        bpy.utils.unregister_class(cl)
