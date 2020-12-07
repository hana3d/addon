import bpy
from bpy.types import UIList

from ...config import HANA3D_NAME


class RENDER_UL_List(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        show_image = layout.operator(f'{HANA3D_NAME}.show_image', icon='FULLSCREEN_ENTER')
        show_image.index = item.index

        # layout.prop(item, 'name', text='', icon = item.icon_id, emboss=False, translate=False)
        layout.label(text=item.name, icon_value=item.icon_id)

        remove_render = layout.operator(f'{HANA3D_NAME}.remove_render', icon='CANCEL', text='')
        remove_render.job_id = item.job_id


classes = (
    RENDER_UL_List,
)

keymaps = []


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
