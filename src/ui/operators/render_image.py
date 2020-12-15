"""Render image operator."""
import bpy

from ....config import HANA3D_NAME
from ....report_tools import execute_wrapper
from ...upload import upload


class ShowRenderImage(bpy.types.Operator):
    """Show render image."""

    bl_idname = f'{HANA3D_NAME}.show_image'
    bl_label = ''

    index: bpy.props.IntProperty(
        name='index',
    )

    @execute_wrapper
    def execute(self, context):
        """Execute the operator.

        Parameters:
            context: context"""
        asset_props = upload.get_upload_props()
        filepath = asset_props.render_list[self.index]['file_path']

        image = bpy.data.images.load(filepath, check_existing=True)
        image.name = asset_props.render_list[self.index]['name']
        asset_props.render_list[self.index]['name'] = image.name

        bpy.ops.render.view_show('INVOKE_DEFAULT')
        try_again = True
        while try_again:
            try_again = self.set_image(bpy.context)

        return {'FINISHED'}

    def set_image(self, context):
        """Set image to the new window.

        Parameters:
            context: context"""
        try:
            context.area.spaces.active.image = image
        except AttributeError:
            try_again = True
        else:
            try_again = False
        return try_again


classes = (
    ShowRenderImage,
)


def register():
    """Register."""
    for cl in classes:
        bpy.utils.register_class(cl)


def unregister():
    """Unregister."""
    for cl in reversed(classes):
        bpy.utils.unregister_class(cl)
