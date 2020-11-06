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

import json
import os
import subprocess
import tempfile

import bpy

from . import bg_blender, colors, paths, ui, utils
from .report_tools import execute_wrapper
from .config import HANA3D_NAME

HANA3D_EXPORT_DATA_FILE = HANA3D_NAME + "_data.json"


def generate_model_thumbnail(
        props=None,
        asset_name: str = None,
        save_only: bool = False,
        blend_filepath: str = ''):
    if props is None:
        props = bpy.data.objects[asset_name].hana3d
        update_state = False
    else:
        update_state = True
    mainmodel = utils.get_active_model()
    assert mainmodel.hana3d.view_id == props.view_id, 'Error when checking for active asset'
    if update_state:
        mainmodel.hana3d.is_generating_thumbnail = True
        mainmodel.hana3d.thumbnail_generating_state = 'starting blender instance'

    binary_path = bpy.app.binary_path
    script_path = os.path.dirname(os.path.realpath(__file__))
    basename, ext = os.path.splitext(bpy.data.filepath)
    if not basename:
        basename = os.path.join(basename, "temp")
    if not ext:
        ext = ".blend"
    asset_name = mainmodel.name
    tempdir = tempfile.mkdtemp()

    file_dir = os.path.dirname(bpy.data.filepath)
    thumb_path = os.path.join(file_dir, asset_name)
    rel_thumb_path = os.path.join('//', asset_name)

    i = 0
    while os.path.isfile(thumb_path + '.jpg'):
        thumb_path = os.path.join(file_dir, asset_name + '_' + str(i).zfill(4))
        rel_thumb_path = os.path.join('//', asset_name + '_' + str(i).zfill(4))
        i += 1

    filepath = os.path.join(tempdir, "thumbnailer_hana3d" + ext)
    tfpath = paths.get_thumbnailer_filepath()
    datafile = os.path.join(tempdir, HANA3D_EXPORT_DATA_FILE)

    autopack = False
    if bpy.data.use_autopack is True:
        autopack = True
        bpy.ops.file.autopack_toggle()

    utils.save_file(filepath, compress=False, copy=True)
    obs = utils.get_hierarchy(mainmodel)
    obnames = []
    for ob in obs:
        obnames.append(ob.name)
    with open(datafile, 'w') as s:
        json.dump(
            {
                "type": "model",
                "models": str(obnames),
                "thumbnail_angle": props.thumbnail_angle,
                "thumbnail_snap_to": props.thumbnail_snap_to,
                "thumbnail_background_lightness": props.thumbnail_background_lightness,
                "thumbnail_resolution": props.thumbnail_resolution,
                "thumbnail_samples": props.thumbnail_samples,
                "thumbnail_denoising": props.thumbnail_denoising,
                "save_only": save_only,
                "blend_filepath": blend_filepath,
            },
            s,
        )
    proc = subprocess.Popen(
        [
            binary_path,
            "--background",
            "-noaudio",
            tfpath,
            "--python",
            os.path.join(script_path, "autothumb_model_bg.py"),
            "--",
            datafile,
            filepath,
            thumb_path,
            tempdir,
        ],
        bufsize=1,
        stdout=subprocess.PIPE,
        stdin=subprocess.PIPE,
        creationflags=utils.get_process_flags(),
    )

    eval_path_computing = "bpy.data.objects['%s'].hana3d.is_generating_thumbnail" % mainmodel.name  # noqa E501
    eval_path_state = "bpy.data.objects['%s'].hana3d.thumbnail_generating_state" % mainmodel.name  # noqa E501
    eval_path = "bpy.data.objects['%s']" % mainmodel.name

    bg_blender.add_bg_process(
        eval_path_computing=eval_path_computing,
        eval_path_state=eval_path_state,
        eval_path=eval_path,
        process_type='THUMBNAILER',
        process=proc,
    )

    if not save_only and update_state:
        mainmodel.hana3d.thumbnail = rel_thumb_path + '.jpg'
    if update_state:
        mainmodel.hana3d.thumbnail_generating_state = 'Saving .blend file'

    if autopack is True:
        bpy.ops.file.autopack_toggle()


class GenerateModelThumbnailOperator(bpy.types.Operator):
    """Generate Cycles thumbnail for model assets"""

    bl_idname = "object.hana3d_thumbnail"
    bl_label = "Hana3D Thumbnail Generator"
    bl_options = {'REGISTER', 'INTERNAL'}

    @classmethod
    def poll(cls, context):
        return bpy.context.view_layer.objects.active is not None

    def draw(self, context):
        ob = bpy.context.active_object
        while ob.parent is not None:
            ob = ob.parent
        props = ob.hana3d
        layout = self.layout
        layout.label(text='thumbnailer settings')
        layout.prop(props, 'thumbnail_background_lightness')
        layout.prop(props, 'thumbnail_angle')
        layout.prop(props, 'thumbnail_snap_to')
        layout.prop(props, 'thumbnail_samples')
        layout.prop(props, 'thumbnail_resolution')
        layout.prop(props, 'thumbnail_denoising')
        preferences = bpy.context.preferences.addons[HANA3D_NAME].preferences
        layout.prop(preferences, "thumbnail_use_gpu")

    @execute_wrapper
    def execute(self, context):
        try:
            props = utils.get_active_model(context).hana3d
            generate_model_thumbnail(props)
        except Exception as e:
            props.is_generating_thumbnail = False
            props.thumbnail_generating_state = ''
            ui.add_report(f'Error in thumbnailer: {e}', color=colors.RED)
            return {'CANCELLED'}
        return {'FINISHED'}

    def invoke(self, context, event):
        wm = context.window_manager
        if bpy.data.filepath == '':
            title = "Can't render thumbnail"
            message = "please save your file first"
            utils.show_pop_menu(message, title)

            return {'CANCELLED'}

        return wm.invoke_props_dialog(self)


def generate_material_thumbnail(
        props=None,
        asset_name: str = None,
        save_only: bool = False,
        blend_filepath: str = ''):
    if props is None:
        props = bpy.data.materials[asset_name].hana3d
        update_state = False
    else:
        update_state = True
    mat = utils.get_active_material()
    assert mat.hana3d.view_id == props.view_id, 'Error when checking active material'
    if update_state:
        mat.hana3d.is_generating_thumbnail = True
        mat.hana3d.thumbnail_generating_state = 'starting blender instance'

    binary_path = bpy.app.binary_path
    script_path = os.path.dirname(os.path.realpath(__file__))
    basename, ext = os.path.splitext(bpy.data.filepath)
    if not basename:
        basename = os.path.join(basename, "temp")
    if not ext:
        ext = ".blend"
    asset_name = mat.name
    tempdir = tempfile.mkdtemp()

    file_dir = os.path.dirname(bpy.data.filepath)

    thumb_path = os.path.join(file_dir, asset_name)
    rel_thumb_path = os.path.join('//', mat.name)
    i = 0
    while os.path.isfile(thumb_path + '.png'):
        thumb_path = os.path.join(file_dir, mat.name + '_' + str(i).zfill(4))
        rel_thumb_path = os.path.join('//', mat.name + '_' + str(i).zfill(4))
        i += 1

    filepath = os.path.join(tempdir, "material_thumbnailer_cycles" + ext)
    tfpath = paths.get_material_thumbnailer_filepath()
    datafile = os.path.join(tempdir, HANA3D_EXPORT_DATA_FILE)

    utils.save_file(filepath, compress=False, copy=True)

    with open(datafile, 'w') as s:
        json.dump(
            {
                "type": "material",
                "material": mat.name,
                "thumbnail_type": props.thumbnail_generator_type,
                "thumbnail_scale": props.thumbnail_scale,
                "thumbnail_background": props.thumbnail_background,
                "thumbnail_background_lightness": props.thumbnail_background_lightness,
                "thumbnail_resolution": props.thumbnail_resolution,
                "thumbnail_samples": props.thumbnail_samples,
                "thumbnail_denoising": props.thumbnail_denoising,
                "adaptive_subdivision": props.adaptive_subdivision,
                "texture_size_meters": props.texture_size_meters,
                "save_only": save_only,
                "blend_filepath": blend_filepath,
            },
            s,
        )

    proc = subprocess.Popen(
        [
            binary_path,
            "--background",
            "-noaudio",
            tfpath,
            "--python",
            os.path.join(script_path, "autothumb_material_bg.py"),
            "--",
            datafile,
            filepath,
            thumb_path,
            tempdir,
        ],
        bufsize=1,
        stdout=subprocess.PIPE,
        stdin=subprocess.PIPE,
        creationflags=utils.get_process_flags(),
    )

    eval_path_computing = "bpy.data.materials['%s'].hana3d.is_generating_thumbnail" % mat.name  # noqa: E501
    eval_path_state = "bpy.data.materials['%s'].hana3d.thumbnail_generating_state" % mat.name  # noqa: E501
    eval_path = "bpy.data.materials['%s']" % mat.name

    bg_blender.add_bg_process(
        eval_path_computing=eval_path_computing,
        eval_path_state=eval_path_state,
        eval_path=eval_path,
        process_type='THUMBNAILER',
        process=proc,
    )

    if not save_only and update_state:
        mat.hana3d.thumbnail = rel_thumb_path + '.png'
    if update_state:
        mat.hana3d.thumbnail_generating_state = 'Saving .blend file'


class GenerateMaterialThumbnailOperator(bpy.types.Operator):
    """Generate Cycles thumbnail for materials"""

    bl_idname = "material.hana3d_thumbnail"
    bl_label = "Hana3D Material Thumbnail Generator"
    bl_options = {'REGISTER', 'INTERNAL'}

    @classmethod
    def poll(cls, context):
        return bpy.context.view_layer.objects.active is not None

    def check(self, context):
        return True

    def draw(self, context):
        layout = self.layout
        props = utils.get_active_material(context).hana3d
        layout.prop(props, 'thumbnail_generator_type')
        layout.prop(props, 'thumbnail_scale')
        layout.prop(props, 'thumbnail_background')
        if props.thumbnail_background:
            layout.prop(props, 'thumbnail_background_lightness')
        layout.prop(props, 'thumbnail_resolution')
        layout.prop(props, 'thumbnail_samples')
        layout.prop(props, 'thumbnail_denoising')
        layout.prop(props, 'adaptive_subdivision')
        preferences = context.preferences.addons[HANA3D_NAME].preferences
        layout.prop(preferences, "thumbnail_use_gpu")

    @execute_wrapper
    def execute(self, context):
        try:
            props = utils.get_active_material(context).hana3d
            generate_material_thumbnail(props)
        except Exception as e:
            props.is_generating_thumbnail = False
            props.thumbnail_generating_state = ''
            self.report({'WARNING'}, "Error while packing file: %s" % str(e))
            return {'CANCELLED'}
        return {'FINISHED'}

    def invoke(self, context, event):
        wm = context.window_manager
        if bpy.data.filepath == '':
            title = "Can't render thumbnail"
            message = "please save your file first"
            utils.show_pop_menu(message, title)

            return {'CANCELLED'}

        return wm.invoke_props_dialog(self)


def get_active_scene(context=None, view_id: str = None):
    context = context or bpy.context
    if view_id is None:
        return context.scene
    scenes = [s for s in context.blend_data.scenes if s.view_id == view_id]

    return scenes[0]


def generate_scene_thumbnail(
        props=None,
        asset_name: str = None,
        save_only: bool = False,
        blend_filepath: str = ''):
    if props is None:
        props = bpy.data.scenes[asset_name].hana3d
        update_state = False
    else:
        update_state = True
    context = bpy.context
    if update_state:
        props.is_generating_thumbnail = True
        props.thumbnail_generating_state = 'starting blender instance'

    basename, ext = os.path.splitext(bpy.data.filepath)
    if not basename:
        basename = os.path.join(basename, "temp")
    if not ext:
        ext = ".blend"

    asset_name = os.path.basename(basename)
    file_dir = os.path.dirname(bpy.data.filepath)
    thumb_path = os.path.join(file_dir, asset_name)
    rel_thumb_path = os.path.join('//', asset_name)

    i = 0
    while os.path.isfile(thumb_path + '.png'):
        thumb_path = os.path.join(file_dir, asset_name + '_' + str(i).zfill(4))
        rel_thumb_path = os.path.join('//', asset_name + '_' + str(i).zfill(4))
        i += 1

    user_preferences = context.preferences.addons[HANA3D_NAME].preferences

    if user_preferences.thumbnail_use_gpu:
        context.scene.cycles.device = 'GPU'

    context.scene.cycles.samples = props.thumbnail_samples
    context.view_layer.cycles.use_denoising = props.thumbnail_denoising

    x = context.scene.render.resolution_x
    y = context.scene.render.resolution_y

    context.scene.render.resolution_x = int(props.thumbnail_resolution)
    context.scene.render.resolution_y = int(props.thumbnail_resolution)

    if save_only:
        bpy.ops.wm.save_as_mainfile(filepath=blend_filepath, compress=True, copy=True)
    else:
        context.scene.render.filepath = thumb_path + '.png'
        bpy.ops.render.render(write_still=True, animation=False)
        props.thumbnail = rel_thumb_path + '.png'

    context.scene.render.resolution_x = x
    context.scene.render.resolution_y = y


class GenerateSceneThumbnailOperator(bpy.types.Operator):
    """Generate Cycles thumbnail for scene"""

    bl_idname = "scene.hana3d_thumbnail"
    bl_label = "Hana3D Thumbnail Generator"
    bl_options = {'REGISTER', 'INTERNAL'}

    def draw(self, context):
        ob = bpy.context.active_object
        while ob.parent is not None:
            ob = ob.parent
        props = ob.hana3d
        layout = self.layout
        layout.label(text='thumbnailer settings')
        layout.prop(props, 'thumbnail_samples')
        layout.prop(props, 'thumbnail_resolution')
        layout.prop(props, 'thumbnail_denoising')
        preferences = bpy.context.preferences.addons[HANA3D_NAME].preferences
        layout.prop(preferences, "thumbnail_use_gpu")

    @execute_wrapper
    def execute(self, context):
        try:
            props = get_active_scene(context).hana3d
            generate_scene_thumbnail(props)
        except Exception as e:
            self.report({'WARNING'}, "Error while exporting file: %s" % str(e))
            return {'CANCELLED'}
        finally:
            props.thumbnail_generating_state = 'Finished'
            props.is_generating_thumbnail = False
        return {'FINISHED'}

    def invoke(self, context, event):
        wm = context.window_manager
        if bpy.data.filepath == '':
            title = "Can't render thumbnail"
            message = "please save your file first"
            utils.show_pop_menu(message, title)

            return {'CANCELLED'}

        return wm.invoke_props_dialog(self)


classes = (
    GenerateModelThumbnailOperator,
    GenerateMaterialThumbnailOperator,
    GenerateSceneThumbnailOperator,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
