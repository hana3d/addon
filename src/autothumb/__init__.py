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

import asyncio
import json
import math
import os
import subprocess
import tempfile
import uuid

import bpy
from mathutils import Euler, Vector

from .. import async_loop
from ... import bg_blender, paths, utils
from ...config import HANA3D_DESCRIPTION, HANA3D_NAME
from ...report_tools import execute_wrapper

HANA3D_EXPORT_DATA_FILE = f"{HANA3D_NAME}_data.json"

BACKGROUND_DEFAULT_COLOR = (1, 1, 1, 1)
CAMERA_DEFAULT_LOCATION = (-3.1068, -3.14043, 2.3688)
CAMERA_DEFAULT_ROTATION = (1.1122483015060425, -8.048914423852693e-08, -0.7800155878067017)
LIGHT_DEFAULT_LOCATION = (2, -4.76656, 3.33653)


def center_objs_for_thumbnail(objs, scene, camera, light):
    parent = objs[0]
    while parent.parent is not None:
        parent = parent.parent
    parent.rotation_euler = (0, 0, 0)

    minx, miny, minz, maxx, maxy, maxz = utils.get_bounds_worldspace(objs)

    cx = (maxx - minx) / 2 + minx
    cy = (maxy - miny) / 2 + miny

    parent.location += Vector((-cx, -cy, -minz))

    camera.location.z = (maxz - minz) / 2
    light.location.z = (maxz - minz) / 2
    dx = maxx - minx
    dy = maxy - miny
    dz = maxz - minz
    r = math.sqrt(dx * dx + dy * dy + dz * dz)

    # scaler = bpy.context.view_layer.objects['scaler']
    # scaler.scale = (r, r, r)
    coef = 0.7
    r *= coef
    camera.scale = (r, r, r)
    light.scale = (r, r, r)
    bpy.context.view_layer.update()


def copy_objects(parent, scene):
    def recursive_copy(parent_original, parent_copy, copies):
        for child in parent_original.children:
            copy = child.copy()
            copy.parent = parent_copy
            copies.append(copy)
            scene.collection.objects.link(copy)
            recursive_copy(child, copy, copies)

    parent_copy = parent.copy()
    copies = [parent_copy]
    scene.collection.objects.link(parent_copy)
    recursive_copy(parent, parent_copy, copies)

    return copies


async def async_thumbnailer(parent, context):
    scene = bpy.data.scenes.new("thumbnailer_scene")

    world = bpy.data.worlds.new("thumbnailer_world")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = BACKGROUND_DEFAULT_COLOR
    scene.world = world

    light_data = bpy.data.lights.new("thumbnailer_light_data", "POINT")
    light = bpy.data.objects.new("thumbnailer_light", light_data)
    light_axis = bpy.data.objects.new("thumbnailer_light_axis", None)
    scene.collection.objects.link(light)
    scene.collection.objects.link(light_axis)
    light.location.x = LIGHT_DEFAULT_LOCATION[0]
    light.location.y = LIGHT_DEFAULT_LOCATION[1]
    light.location.z = LIGHT_DEFAULT_LOCATION[2]
    light.parent = light_axis

    camera_data = bpy.data.cameras.new("thumbnailer_camera_data")
    camera = bpy.data.objects.new("thumbnailer_camera", camera_data)
    camera_axis = bpy.data.objects.new("thumbnailer_camera_axis", None)
    scene.collection.objects.link(camera)
    scene.collection.objects.link(camera_axis)
    scene.camera = camera
    camera.location.x = CAMERA_DEFAULT_LOCATION[0]
    camera.location.y = CAMERA_DEFAULT_LOCATION[1]
    camera.location.z = CAMERA_DEFAULT_LOCATION[2]
    camera.rotation_mode = "XYZ"
    camera.rotation_euler = Euler(CAMERA_DEFAULT_ROTATION, "XYZ")
    camera.parent = camera_axis

    copies = copy_objects(parent, scene)
    center_objs_for_thumbnail(copies, scene, camera_axis, light_axis)

    scene.render.engine = "CYCLES"
    user_preferences = context.preferences.addons[HANA3D_NAME].preferences
    if user_preferences.thumbnail_use_gpu:
        scene.cycles.device = "GPU"
    scene.render.resolution_x = 512
    scene.render.resolution_y = 512
    scene.render.image_settings.file_format = "JPEG"

    filepath = f"{paths.get_temp_dir('thumbnailer')}/{uuid.uuid4()}.png"
    scene.render.filepath = filepath
    bpy.ops.render.render(write_still=True, animation=False, scene=scene.name)

    for copy in copies:
        bpy.data.objects.remove(copy)
    bpy.data.worlds.remove(world)
    bpy.data.objects.remove(camera_axis)
    bpy.data.objects.remove(camera)
    bpy.data.cameras.remove(camera_data)
    bpy.data.objects.remove(light_axis)
    bpy.data.objects.remove(light)
    bpy.data.lights.remove(light_data)
    bpy.data.scenes.remove(scene)

    return filepath


def thumbnailer_done(task):
    print('Task result: ', task.result())


class ModelThumbnailerOperator(bpy.types.Operator):
    """Generate Cycles thumbnail for model assets"""

    bl_idname = f"object.{HANA3D_NAME}_thumbnail"
    bl_label = f"{HANA3D_DESCRIPTION} Thumbnail Generator"
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        model = bpy.context.object
        async_task = asyncio.ensure_future(async_thumbnailer(model, context))
        async_task.add_done_callback(thumbnailer_done)
        async_loop.ensure_async_loop()

        return {'FINISHED'}


def generate_material_thumbnail(
        props=None,
        asset_name: str = None,
        save_only: bool = False,
        blend_filepath: str = ''):
    if props is None:
        props = getattr(bpy.data.materials[asset_name], HANA3D_NAME)
        update_state = False
    else:
        update_state = True
    mat = utils.get_active_material()
    material_props = getattr(mat, HANA3D_NAME)
    assert material_props.view_id == props.view_id, 'Error when checking active material'
    if update_state:
        material_props.is_generating_thumbnail = True
        material_props.thumbnail_generating_state = 'starting blender instance'

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
            HANA3D_NAME,
        ],
        bufsize=1,
        stdout=subprocess.PIPE,
        stdin=subprocess.PIPE,
        creationflags=utils.get_process_flags(),
    )

    eval_path_computing = "getattr(bpy.data.materials['%s'], '%s').is_generating_thumbnail" % (mat.name, HANA3D_NAME)  # noqa: E501
    eval_path_state = "getattr(bpy.data.materials['%s'], '%s').thumbnail_generating_state" % (mat.name, HANA3D_NAME)  # noqa: E501
    eval_path = "bpy.data.materials['%s']" % mat.name

    bg_blender.add_bg_process(
        eval_path_computing=eval_path_computing,
        eval_path_state=eval_path_state,
        eval_path=eval_path,
        process_type='THUMBNAILER',
        process=proc,
    )

    if not save_only and update_state:
        material_props.thumbnail = rel_thumb_path + '.png'
    if update_state:
        material_props.thumbnail_generating_state = 'Saving .blend file'


class GenerateMaterialThumbnailOperator(bpy.types.Operator):
    """Generate Cycles thumbnail for materials"""

    bl_idname = f"material.{HANA3D_NAME}_thumbnail"
    bl_label = f"{HANA3D_DESCRIPTION} Material Thumbnail Generator"
    bl_options = {'REGISTER', 'INTERNAL'}

    @classmethod
    def poll(cls, context):
        return bpy.context.view_layer.objects.active is not None

    def check(self, context):
        return True

    def draw(self, context):
        layout = self.layout
        props = getattr(utils.get_active_material(context), HANA3D_NAME)
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
            props = getattr(utils.get_active_material(context), HANA3D_NAME)
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
        props = getattr(bpy.data.scenes[asset_name], HANA3D_NAME)
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

    bl_idname = f"scene.{HANA3D_NAME}_thumbnail"
    bl_label = f"{HANA3D_DESCRIPTION} Thumbnail Generator"
    bl_options = {'REGISTER', 'INTERNAL'}

    def draw(self, context):
        ob = bpy.context.active_object
        while ob.parent is not None:
            ob = ob.parent
        props = getattr(ob, HANA3D_NAME)
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
            props = getattr(get_active_scene(context), HANA3D_NAME)
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
    ModelThumbnailerOperator,
    GenerateMaterialThumbnailOperator,
    GenerateSceneThumbnailOperator,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
