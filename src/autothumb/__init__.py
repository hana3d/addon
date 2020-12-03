"""Automatic thumbnailer."""
import json
import logging
import os
import pathlib
import tempfile
from typing import Callable, Union

import bpy

from ... import colors, paths, ui, utils
from ...config import HANA3D_DESCRIPTION, HANA3D_NAME
from ...report_tools import execute_wrapper
from ..async_loop import run_async_function
from ..subprocess_async.subprocess_async import Subprocess

HANA3D_EXPORT_DATA_FILE = f"{HANA3D_NAME}_data.json"


def _common_setup(
        props,
        asset_name: str,
        asset_type: str,
        json_data: dict,
        thumb_path: Union[str, pathlib.Path],
        done_callback: Callable):
    props.is_generating_thumbnail = True
    props.thumbnail_generating_state = 'starting blender instance'

    binary_path = bpy.app.binary_path
    script_path = os.path.dirname(os.path.realpath(__file__))
    basename, ext = os.path.splitext(bpy.data.filepath)
    if not basename:
        basename = os.path.join(basename, "temp")
    if not ext:
        ext = ".blend"
    tempdir = tempfile.mkdtemp()

    filepath = os.path.join(tempdir, "thumbnailer_" + HANA3D_NAME + ext)
    tfpath = paths.get_thumbnailer_filepath(asset_type)
    datafile = os.path.join(tempdir, HANA3D_EXPORT_DATA_FILE)

    if bpy.data.use_autopack is True:
        bpy.ops.file.autopack_toggle()
    utils.save_file(filepath, compress=False, copy=True)

    with open(datafile, 'w') as json_file:
        json.dump(json_data, json_file)

    cmd = [
        binary_path,
        '--background',
        '-noaudio',
        tfpath,
        '--python',
        os.path.join(script_path, f'{asset_type}_bg.py'),
        '--',
        datafile,
        filepath,
        thumb_path,
        tempdir,
        HANA3D_NAME,
    ]

    subprocess = Subprocess()
    props.thumbnail_generating_state = 'rendering thumbnail'
    run_async_function(subprocess.subprocess, done_callback=done_callback, cmd=cmd)


class GenerateModelThumbnailOperator(bpy.types.Operator):
    """Generate Cycles thumbnail for model assets."""

    bl_idname = f"object.{HANA3D_NAME}_thumbnail"
    bl_label = f"{HANA3D_DESCRIPTION} Thumbnail Generator"
    bl_options = {'REGISTER', 'INTERNAL'}

    @classmethod
    def poll(cls, context):
        return bpy.context.view_layer.objects.active is not None

    def draw(self, context):
        ob = bpy.context.active_object
        while ob.parent is not None:
            ob = ob.parent
        props = getattr(ob, HANA3D_NAME)
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
            main_model = utils.get_active_model(context)
            self.props = getattr(main_model, HANA3D_NAME)
            self._generate_model_thumbnail(main_model)
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

    def _done_callback(self, task):
        self.props.thumbnail = self.rel_thumb_path + '.jpg'
        self.props.thumbnail_generating_state = 'rendering done'
        self.props.is_generating_thumbnail = False

        if bpy.data.use_autopack is True:
            bpy.ops.file.autopack_toggle()

    def _generate_model_thumbnail(
            self,
            main_model: bpy.types.Object,
            asset_name: str = None,
            save_only: bool = False,
            blend_filepath: str = ''):
        mainmodel = utils.get_active_model()
        if asset_name is None:
            asset_name = mainmodel.name

        obs = utils.get_hierarchy(mainmodel)
        obnames = []
        for ob in obs:
            obnames.append(ob.name)

        json_data = {
            "type": "model",
            "models": str(obnames),
            "thumbnail_angle": self.props.thumbnail_angle,
            "thumbnail_snap_to": self.props.thumbnail_snap_to,
            "thumbnail_background_lightness": self.props.thumbnail_background_lightness,
            "thumbnail_resolution": self.props.thumbnail_resolution,
            "thumbnail_samples": self.props.thumbnail_samples,
            "thumbnail_denoising": self.props.thumbnail_denoising,
            "save_only": save_only,
            "blend_filepath": blend_filepath,
        }

        file_dir = os.path.dirname(bpy.data.filepath)
        thumb_path = os.path.join(file_dir, asset_name)
        self.rel_thumb_path = os.path.join('//', asset_name)

        i = 0
        while os.path.isfile(thumb_path + '.jpg'):
            thumb_path = os.path.join(file_dir, asset_name + '_' + str(i).zfill(4))
            self.rel_thumb_path = os.path.join('//', asset_name + '_' + str(i).zfill(4))
            i += 1

        _common_setup(self.props, asset_name, 'model', json_data, thumb_path, self._done_callback)


class GenerateMaterialThumbnailOperator(bpy.types.Operator):
    """Generate Cycles thumbnail for materials."""

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
            material = utils.get_active_material(context)
            self.props = getattr(material, HANA3D_NAME)
            self._generate_material_thumbnail(material)
        except Exception as e:
            props.is_generating_thumbnail = False
            props.thumbnail_generating_state = ''
            logging.warning(f'Error while packing file: {str(e)}')
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

    def _done_callback(self, task):
        self.props.thumbnail = self.rel_thumb_path + '.jpg'
        self.props.thumbnail_generating_state = 'rendering done'
        self.props.is_generating_thumbnail = False

        if bpy.data.use_autopack is True:
            bpy.ops.file.autopack_toggle()

    def _generate_material_thumbnail(
            self,
            material: bpy.types.Material,
            asset_name: str = None,
            save_only: bool = False,
            blend_filepath: str = ''):
        if asset_name is None:
            asset_name = mat.name

        json_data = {
            "type": "material",
            "material": material.name,
            "thumbnail_type": self.props.thumbnail_generator_type,
            "thumbnail_scale": self.props.thumbnail_scale,
            "thumbnail_background": self.props.thumbnail_background,
            "thumbnail_background_lightness": self.props.thumbnail_background_lightness,
            "thumbnail_resolution": self.props.thumbnail_resolution,
            "thumbnail_samples": self.props.thumbnail_samples,
            "thumbnail_denoising": self.props.thumbnail_denoising,
            "adaptive_subdivision": self.props.adaptive_subdivision,
            "texture_size_meters": self.props.texture_size_meters,
            "save_only": save_only,
            "blend_filepath": blend_filepath,
        }

        file_dir = os.path.dirname(bpy.data.filepath)
        thumb_path = os.path.join(file_dir, asset_name)
        self.rel_thumb_path = os.path.join('//', asset_name)

        i = 0
        while os.path.isfile(thumb_path + '.jpg'):
            thumb_path = os.path.join(file_dir, asset_name + '_' + str(i).zfill(4))
            self.rel_thumb_path = os.path.join('//', asset_name + '_' + str(i).zfill(4))
            i += 1

        _common_setup(self.props, asset_name, 'material',
                      json_data, thumb_path, self._done_callback)


class GenerateSceneThumbnailOperator(bpy.types.Operator):
    """Generate Cycles thumbnail for scene."""

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

    def get_active_scene(self, context=None, view_id: str = None):
        context = context or bpy.context
        if view_id is None:
            return context.scene
        scenes = [s for s in context.blend_data.scenes if s.view_id == view_id]

        return scenes[0]

    def generate_scene_thumbnail(
            self,
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

    @execute_wrapper
    def execute(self, context):
        try:
            props = getattr(self.get_active_scene(context), HANA3D_NAME)
            self.generate_scene_thumbnail(props)
        except Exception as e:
            logging.warning(f'Error while exporting file: {str(e)}')
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
    """Autothumb register."""
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    """Autothumb unregister."""
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
