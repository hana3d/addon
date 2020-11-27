import uuid

import bpy

from .. import async_loop
from ... import paths
from ...config import HANA3D_DESCRIPTION, HANA3D_NAME
# from ...report_tools import execute_wrapper


class SceneThumbnailerOperator(async_loop.AsyncModalOperatorMixin, bpy.types.Operator):
    """Generate Cycles thumbnail for model assets"""

    bl_idname = f'scene.{HANA3D_NAME}_thumbnail'
    bl_label = f'{HANA3D_DESCRIPTION} Thumbnail Generator'
    bl_options = {'REGISTER', 'INTERNAL'}

    async def render(self):
        filepath = f'{paths.get_temp_dir("thumbnailer")}/{uuid.uuid4()}.png'
        self.scene.render.filepath = filepath
        bpy.ops.render.render(write_still=True, animation=False, scene=self.scene.name)

    async def async_execute(self, context):

        self.scene = context.scene
        if self.scene.camera is None:
            self.report({'ERROR'}, 'No active camera in scene')

        props.is_generating_thumbnail = True
        props.thumbnail_generating_state = 'rendering thumbnail'
        await self.render()
        props.thumbnail_generating_state = 'thumbnailer finished successfully'
        props.is_generating_thumbnail = False

        self._state = 'QUIT'


def register():
    bpy.utils.register_class(SceneThumbnailerOperator)


def unregister():
    bpy.utils.unregister_class(SceneThumbnailerOperator)
