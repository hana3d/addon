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

if 'bpy' in locals():
    from importlib import reload

    bg_blender = reload(bg_blender)
    paths = reload(paths)
    utils = reload(utils)
else:
    from hana3d import bg_blender, paths, utils

import json
import os
import subprocess
import tempfile

import bpy

HANA3D_EXPORT_DATA_FILE = "data.json"


def check_thumbnail(props, imgpath):
    img = utils.get_hidden_image(imgpath, 'upload_preview', force_reload=True)
    if img is not None:  # and img.size[0] == img.size[1] and img.size[0] >= 512 and (
        # img.file_format == 'JPEG' or img.file_format == 'PNG'):
        props.has_thumbnail = True
        props.thumbnail_generating_state = ''
        return
    else:
        props.has_thumbnail = False
    output = ''
    if img is None or img.size[0] == 0 or img.filepath.find('thumbnail_notready.jpg') > -1:
        output += 'No thumbnail or wrong file path\n'
    else:
        pass
        # this is causing problems on some platforms, don't know why..
        # if img.size[0] != img.size[1]:
        #     output += 'image not a square\n'
        # if img.size[0] < 512:
        #     output += 'image too small, should be at least 512x512\n'
        # if img.file_format != 'JPEG' or img.file_format != 'PNG':
        #     output += 'image has to be a jpeg or png'
    props.thumbnail_generating_state = output


def update_upload_model_preview(self, context):
    ob = utils.get_active_model()
    if ob is not None:
        props = ob.hana3d
        imgpath = props.thumbnail
        check_thumbnail(props, imgpath)


def update_upload_scene_preview(self, context):
    s = bpy.context.scene
    props = s.hana3d
    imgpath = props.thumbnail
    check_thumbnail(props, imgpath)


def update_upload_material_preview(self, context):
    if (
        hasattr(bpy.context, 'active_object')
        and bpy.context.view_layer.objects.active is not None
        and bpy.context.active_object.active_material is not None
    ):
        mat = bpy.context.active_object.active_material
        props = mat.hana3d
        imgpath = props.thumbnail
        check_thumbnail(props, imgpath)


def start_thumbnailer(self, context):
    # Prepare to save the file
    mainmodel = utils.get_active_model()
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
    try:
        autopack = False
        if bpy.data.use_autopack is True:
            autopack = True
            bpy.ops.file.autopack_toggle()
        # save a copy of actual scene but don't interfere with the users models
        bpy.ops.wm.save_as_mainfile(filepath=filepath, compress=False, copy=True)

        obs = utils.get_hierarchy(mainmodel)
        obnames = []
        for ob in obs:
            obnames.append(ob.name)
        with open(datafile, 'w') as s:
            hana3d = mainmodel.hana3d
            json.dump(
                {
                    "type": "model",
                    "models": str(obnames),
                    "thumbnail_angle": hana3d.thumbnail_angle,
                    "thumbnail_snap_to": hana3d.thumbnail_snap_to,
                    "thumbnail_background_lightness": hana3d.thumbnail_background_lightness,
                    "thumbnail_resolution": hana3d.thumbnail_resolution,
                    "thumbnail_samples": hana3d.thumbnail_samples,
                    "thumbnail_denoising": hana3d.thumbnail_denoising,
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

        mainmodel.hana3d.thumbnail = rel_thumb_path + '.jpg'
        mainmodel.hana3d.thumbnail_generating_state = 'Saving .blend file'

        if autopack is True:
            bpy.ops.file.autopack_toggle()

    except Exception as e:
        self.report({'WARNING'}, "Error while exporting file: %s" % str(e))
        return {'FINISHED'}


def start_material_thumbnailer(self, context):
    # Prepare to save the file
    mat = bpy.context.active_object.active_material
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
    try:
        # save a copy of actual scene but don't interfere with the users models
        bpy.ops.wm.save_as_mainfile(filepath=filepath, compress=False, copy=True)

        with open(datafile, 'w') as s:
            hana3d = mat.hana3d
            json.dump(
                {
                    "type": "material",
                    "material": mat.name,
                    "thumbnail_type": hana3d.thumbnail_generator_type,
                    "thumbnail_scale": hana3d.thumbnail_scale,
                    "thumbnail_background": hana3d.thumbnail_background,
                    "thumbnail_background_lightness": hana3d.thumbnail_background_lightness,
                    "thumbnail_resolution": hana3d.thumbnail_resolution,
                    "thumbnail_samples": hana3d.thumbnail_samples,
                    "thumbnail_denoising": hana3d.thumbnail_denoising,
                    "adaptive_subdivision": hana3d.adaptive_subdivision,
                    "texture_size_meters": hana3d.texture_size_meters,
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

        eval_path_computing = "bpy.data.materials['%s'].hana3d.is_generating_thumbnail" % mat.name
        eval_path_state = "bpy.data.materials['%s'].hana3d.thumbnail_generating_state" % mat.name
        eval_path = "bpy.data.materials['%s']" % mat.name

        bg_blender.add_bg_process(
            eval_path_computing=eval_path_computing,
            eval_path_state=eval_path_state,
            eval_path=eval_path,
            process_type='THUMBNAILER',
            process=proc,
        )

        mat.hana3d.thumbnail = rel_thumb_path + '.png'
        mat.hana3d.thumbnail_generating_state = 'Saving .blend file'
    except Exception as e:
        self.report({'WARNING'}, "Error while packing file: %s" % str(e))
        return {'FINISHED'}


def start_scene_thumbnailer(self, context):
    # Prepare to save the file
    s = bpy.context.scene
    props = s.hana3d
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

    try:
        user_preferences = bpy.context.preferences.addons['hana3d'].preferences

        bpy.context.scene.render.filepath = thumb_path + '.png'
        if user_preferences.thumbnail_use_gpu:
            bpy.context.scene.cycles.device = 'GPU'

        bpy.context.scene.cycles.samples = props.thumbnail_samples
        bpy.context.view_layer.cycles.use_denoising = props.thumbnail_denoising

        x = bpy.context.scene.render.resolution_x
        y = bpy.context.scene.render.resolution_y

        bpy.context.scene.render.resolution_x = int(props.thumbnail_resolution)
        bpy.context.scene.render.resolution_y = int(props.thumbnail_resolution)

        bpy.ops.render.render(write_still=True, animation=False)

        bpy.context.scene.render.resolution_x = x
        bpy.context.scene.render.resolution_y = y

        props.thumbnail = rel_thumb_path + '.png'
        props.thumbnail_generating_state = 'Finished'
        props.is_generating_thumbnail = False

    except Exception as e:
        props.is_generating_thumbnail = False
        self.report({'WARNING'}, "Error while exporting file: %s" % str(e))
        return {'FINISHED'}


class GenerateThumbnailOperator(bpy.types.Operator):
    """Generate Cycles thumbnail for model assets"""

    bl_idname = "object.hana3d_generate_thumbnail"
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
        preferences = bpy.context.preferences.addons['hana3d'].preferences
        layout.prop(preferences, "thumbnail_use_gpu")

    def execute(self, context):
        start_thumbnailer(self, context)
        return {'FINISHED'}

    def invoke(self, context, event):
        wm = context.window_manager
        if bpy.data.filepath == '':
            title = "Can't render thumbnail"
            message = "please save your file first"

            def draw_message(self, context):
                self.layout.label(text=message)

            bpy.context.window_manager.popup_menu(draw_message, title=title, icon='INFO')
            return {'FINISHED'}

        return wm.invoke_props_dialog(self)


class GenerateMaterialThumbnailOperator(bpy.types.Operator):
    """Tooltip"""

    bl_idname = "object.hana3d_material_thumbnail"
    bl_label = "Hana3D Material Thumbnail Generator"
    bl_options = {'REGISTER', 'INTERNAL'}

    @classmethod
    def poll(cls, context):
        return bpy.context.view_layer.objects.active is not None

    def check(self, context):
        return True

    def draw(self, context):
        layout = self.layout
        props = bpy.context.active_object.active_material.hana3d
        layout.prop(props, 'thumbnail_generator_type')
        layout.prop(props, 'thumbnail_scale')
        layout.prop(props, 'thumbnail_background')
        if props.thumbnail_background:
            layout.prop(props, 'thumbnail_background_lightness')
        layout.prop(props, 'thumbnail_resolution')
        layout.prop(props, 'thumbnail_samples')
        layout.prop(props, 'thumbnail_denoising')
        layout.prop(props, 'adaptive_subdivision')
        preferences = bpy.context.preferences.addons['hana3d'].preferences
        layout.prop(preferences, "thumbnail_use_gpu")

    def execute(self, context):
        start_material_thumbnailer(self, context)

        return {'FINISHED'}

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self)


class GenerateSceneThumbnailOperator(bpy.types.Operator):
    """Generate Cycles thumbnail for scene"""

    bl_idname = "object.hana3d_scene_thumbnail"
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
        preferences = bpy.context.preferences.addons['hana3d'].preferences
        layout.prop(preferences, "thumbnail_use_gpu")

    def execute(self, context):
        start_scene_thumbnailer(self, context)
        return {'FINISHED'}

    def invoke(self, context, event):
        wm = context.window_manager
        if bpy.data.filepath == '':
            title = "Can't render thumbnail"
            message = "please save your file first"

            def draw_message(self, context):
                self.layout.label(text=message)

            bpy.context.window_manager.popup_menu(draw_message, title=title, icon='INFO')
            return {'FINISHED'}

        return wm.invoke_props_dialog(self)


classes = (
    GenerateThumbnailOperator,
    GenerateMaterialThumbnailOperator,
    GenerateSceneThumbnailOperator,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
