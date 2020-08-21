# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

if "bpy" in locals():
    import importlib

    bg_blender = importlib.reload(bg_blender)
    paths = importlib.reload(paths)
    utils = importlib.reload(utils)
else:
    from hana3d import bg_blender, paths, utils

import json
import os
import subprocess
import tempfile
from collections import defaultdict

import bpy
import bpy.utils.previews
from bpy.types import Operator


class RenderScene(Operator):
    """Render Scene online at notrenderfarm.com"""

    bl_idname = "hana3d.render_scene"
    bl_label = "Render Scene"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return utils.get_active_asset() is not None

    def execute(self, context):
        props = utils.get_upload_props()

        def draw_message(self, context):
            self.layout.label(text=message)
        if props.view_id == '':
            title = "Can't render"
            message = "Please upload selected asset or select uploaded asset"
            bpy.context.window_manager.popup_menu(draw_message, title=title, icon='INFO')
            return {'FINISHED'}
        self.start_render_process(context, props)
        return {'FINISHED'}

    def start_render_process(self, context, props):
        render_props = context.scene.Hana3DRender
        props.rendering = True

        binary_path = bpy.app.binary_path
        script_path = os.path.dirname(os.path.realpath(__file__))
        basename, ext = os.path.splitext(bpy.data.filepath)
        if not basename:
            basename = os.path.join(basename, 'temp')
        if not ext:
            ext = '.blend'

        tempdir = tempfile.mkdtemp()
        filepath = os.path.join(tempdir, 'export_render' + ext)
        datafile = os.path.join(tempdir, 'data.json')

        if render_props.frame_animation == 'FRAME':
            frame_start = context.scene.frame_current
            frame_end = context.scene.frame_current
        elif render_props.frame_animation == 'ANIMATION':
            frame_start = context.scene.frame_start
            frame_end = context.scene.frame_end

        *_, bg_process_params, props = utils.get_export_data(
            context.scene.Hana3DUI.asset_type,
            path_computing='rendering',
            path_state='render_state',
            path_output='render_output',
        )

        try:
            bpy.ops.wm.save_as_mainfile(filepath=filepath, compress=False, copy=True)
            clean_filepath = paths.get_clean_filepath()
            data = {
                'debug_value': bpy.app.debug_value,
                'asset_id': props.id,
                'view_id': props.view_id,
                'engine': render_props.engine,
                'frame_start': frame_start,
                'frame_end': frame_end,
                'filepath': filepath,
                'job_name': props.render_job_name,
            }
            with open(datafile, 'w') as f:
                json.dump(data, f)

            proc = subprocess.Popen(
                [
                    binary_path,
                    "--background",
                    "-noaudio",
                    clean_filepath,
                    "--python",
                    os.path.join(script_path, "render_ops_bg.py"),
                    "--",
                    datafile,
                ],
                bufsize=5000,
                stdout=subprocess.PIPE,
                stdin=subprocess.PIPE,
            )

            bg_blender.add_bg_process(
                process_type='RENDER',
                process=proc,
                **bg_process_params
            )

        except Exception as e:
            print(e)
            props.rendering = False


class ImportRender(Operator):
    """Import finished render job"""

    bl_idname = "hana3d.import_render"
    bl_label = "Import render"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        props = utils.get_upload_props()
        for job in props.render_data['jobs']:
            if job['id'] == props.render_job_output:
                img = bpy.data.images.load(job['file_path'], check_existing=True)
                img.name = job['job_name']

                message = "Your render is now on your scene's Image Data list"

                def draw(self, context):
                    self.layout.label(text=message)
                context.window_manager.popup_menu(draw, title='Success')

                self.report({'INFO'}, message)
                return {'FINISHED'}
        print(f'Cound not find render job id={job["id"]}')
        return {'CANCELLED'}


class RemoveRender(Operator):
    """Remove finished render job"""

    bl_idname = "hana3d.remove_render"
    bl_label = "Remove render"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return False

    def execute(self, context):
        # WIP
        return {'FINISHED'}


class LinkImageAsRender(Operator):
    """Import image as asset render"""

    bl_idname = "hana3d.link_image_as_render"
    bl_label = "Render from image"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return False

    def execute(self, context):
        # WIP
        return {'FINISHED'}


classes = (
    RenderScene,
    ImportRender,
    RemoveRender,
    LinkImageAsRender,
)

# Dictionary to store asset previews. Keys are the view_id's
render_previews = defaultdict(bpy.utils.previews.new)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

    for pcoll in preview_collections.values():
        if pcoll in render_previews.values():
            bpy.utils.previews.remove(pcoll)
    render_previews.clear()
