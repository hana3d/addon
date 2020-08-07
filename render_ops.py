if "bpy" in locals():
    import importlib

    paths = importlib.reload(paths)
    utils = importlib.reload(utils)
    rerequests = importlib.reload(rerequests)
    bg_blender = importlib.reload(bg_blender)
else:
    from hana3d import utils, paths, rerequests, bg_blender

import bpy

import os
import tempfile
import json
import subprocess
from bpy.types import Operator


def update_user():
    render_props = bpy.context.scene.Hana3DRender
    profile = bpy.context.window_manager.get('hana3d profile')
    if profile is not None:
        user = profile.get('user')
        if user is not None:
            headers = utils.get_headers()
            r = rerequests.get(
                paths.get_render_farm_user_url(user['email']),
                headers=headers
            )
            r_json = json.loads(r.content)
            render_props.balance = f'${r_json[0]["balance"]}'
            render_props.user_id = r_json[0]["id"]
        else:
            render_props.balance = '$0.00'
    else:
        render_props.balance = '$0.00'


def upload_scene():
    pass


def create_project():
    pass


def create_job():
    pass


def start_job():
    pass


def timer_job_progress():
    pass


def start_render_process(self, context):
    render_props = context.scene.Hana3DRender
    render_props.rendering = True

    binary_path = bpy.app.binary_path
    script_path = os.path.dirname(os.path.realpath(__file__))
    basename, ext = os.path.splitext(bpy.data.filepath)
    if not basename:
        basename = os.path.join(basename, "temp")
    if not ext:
        ext = ".blend"

    tempdir = tempfile.mkdtemp()
    filepath = os.path.join(tempdir, "export_render" + ext)
    datafile = os.path.join(tempdir, 'data.json')

    if render_props.frame_animation == 'FRAME':
        frame_start = context.scene.frame_current
        frame_end = context.scene.frame_current
    elif render_props.frame_animation == 'ANIMATION':
        frame_start = context.scene.frame_start
        frame_end = context.scene.frame_end

    eval_path_computing = "bpy.context.scene.Hana3DRender.rendering"
    eval_path_state = "bpy.context.scene.Hana3DRender.render_state"
    eval_path = "bpy.context.scene.Hana3DRender.render_path"

    try:
        bpy.ops.wm.save_as_mainfile(filepath=filepath, compress=False, copy=True)
        clean_filepath = paths.get_clean_filepath()
        data = {
            "user_id": render_props.user_id,
            "asset": render_props.asset,
            "engine": render_props.engine,
            "frame_start": frame_start,
            "frame_end": frame_end,
            "source_filepath": filepath,
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
            eval_path_computing=eval_path_computing,
            eval_path_state=eval_path_state,
            eval_path=eval_path,
            process_type='RENDER',
            process=proc,
        )

    except Exception as e:
        print(e)


class RenderScene(Operator):
    """Render Scene online at notrenderfarm.com"""

    bl_idname = "hana3d.render_scene"
    bl_label = "Render Scene"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return not context.scene.Hana3DRender.rendering

    def execute(self, context):
        # props = utils.get_upload_props()

        # def draw_message(self, context):
        #     self.layout.label(text=message)
        # if props is None:
        #     title = "Can't render"
        #     message = "Please select an Asset"
        #     bpy.context.window_manager.popup_menu(draw_message, title=title, icon='INFO')
        #     return {'FINISHED'}
        # elif props.asset_base_id == '':
        #     title = "Can't render"
        #     message = "Please upload asset or select uploaded"
        #     bpy.context.window_manager.popup_menu(draw_message, title=title, icon='INFO')
        #     return {'FINISHED'}
        start_render_process(self, context)
        return {'FINISHED'}


classes = (
    RenderScene,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
