"""Automatic thumbnailer."""
import json
import logging
import os
import pathlib
import tempfile
from typing import Callable, Union

import bpy

from ... import hana3d_types, paths, utils
from ...config import HANA3D_DESCRIPTION, HANA3D_NAME
from ...report_tools import execute_wrapper
from ..asset.asset_type import AssetType
from ..async_loop import run_async_function
from ..subprocess_async.subprocess_async import Subprocess  # noqa: S404
from ..ui import colors
from ..ui.main import UI

HANA3D_EXPORT_DATA_FILE = f'{HANA3D_NAME}_data.json'


def _common_setup(  # noqa: WPS211,WPS210
    props: hana3d_types.Props,
    asset_name: str,
    asset_type: AssetType,
    json_data: dict,
    thumb_path: Union[str, pathlib.Path],
    done_callback: Callable,
):
    props.is_generating_thumbnail = True
    props.thumbnail_generating_state = 'starting blender instance'

    binary_path = bpy.app.binary_path
    script_path = os.path.dirname(os.path.realpath(__file__))
    basename, ext = os.path.splitext(bpy.data.filepath)
    if not basename:
        basename = os.path.join(basename, 'temp')
    if not ext:
        ext = '.blend'
    tempdir = tempfile.mkdtemp()

    filepath = os.path.join(tempdir, f'thumbnailer_{HANA3D_NAME}{ext}')
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

    bl_idname = f'object.{HANA3D_NAME}_thumbnail'
    bl_label = f'{HANA3D_DESCRIPTION} Thumbnail Generator'
    bl_options = {'REGISTER', 'INTERNAL'}

    @classmethod
    def poll(cls, context):
        """Model thumbnailer poll.

        Parameters:
            context: Blender context

        Returns:
            bool: if there is an active object
        """
        return bpy.context.view_layer.objects.active is not None

    def draw(self, context):
        """Model thumbnailer draw.

        Parameters:
            context: Blender context
        """
        ob = context.active_object
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
        preferences = context.preferences.addons[HANA3D_NAME].preferences
        layout.prop(preferences, 'thumbnail_use_gpu')

    @execute_wrapper
    def execute(self, context):
        """Model thumbnailer execute.

        Parameters:
            context: Blender context

        Returns:
            enum set in {‘RUNNING_MODAL’, ‘CANCELLED’, ‘FINISHED’, ‘PASS_THROUGH’, ‘INTERFACE’}
        """
        try:    # noqa: WPS229
            main_model = utils.get_active_model(context)
            self.props = getattr(main_model, HANA3D_NAME)
            self._generate_model_thumbnail(main_model)
        except Exception as error:
            props.is_generating_thumbnail = False
            props.thumbnail_generating_state = ''
            UI().add_report(f'Error in thumbnailer: {error}', color=colors.RED)
            return {'CANCELLED'}
        return {'FINISHED'}

    def invoke(self, context, event):
        """Model thumbnailer invoke.

        Parameters:
            context: Blender context
            event: invoke event

        Returns:
            enum set in {‘RUNNING_MODAL’, ‘CANCELLED’, ‘FINISHED’, ‘PASS_THROUGH’, ‘INTERFACE’}
        """
        wm = context.window_manager
        if bpy.data.filepath == '':
            title = 'Cannot render thumbnail'
            message = 'please save your file first'
            utils.show_pop_menu(message, title)

            return {'CANCELLED'}

        return wm.invoke_props_dialog(self)

    def _done_callback(self, task):
        self.props.thumbnail = f'{self.rel_thumb_path}.jpg'
        self.props.thumbnail_generating_state = 'rendering done'
        self.props.is_generating_thumbnail = False

        if bpy.data.use_autopack is True:
            bpy.ops.file.autopack_toggle()

    def _generate_model_thumbnail(  # noqa: WPS210
        self,
        main_model: bpy.types.Object,
        asset_name: str = None,
        save_only: bool = False,
        blend_filepath: str = '',
    ):
        mainmodel = utils.get_active_model()
        if asset_name is None:
            asset_name = mainmodel.name

        obs = utils.get_hierarchy(mainmodel)
        obnames = []
        for ob in obs:
            obnames.append(ob.name)

        json_data = {
            'type': 'model',
            'models': str(obnames),
            'thumbnail_angle': self.props.thumbnail_angle,
            'thumbnail_snap_to': self.props.thumbnail_snap_to,
            'thumbnail_background_lightness': self.props.thumbnail_background_lightness,
            'thumbnail_resolution': self.props.thumbnail_resolution,
            'thumbnail_samples': self.props.thumbnail_samples,
            'thumbnail_denoising': self.props.thumbnail_denoising,
            'save_only': save_only,
            'blend_filepath': blend_filepath,
        }

        file_dir = os.path.dirname(bpy.data.filepath)
        thumb_path = os.path.join(file_dir, asset_name)
        self.rel_thumb_path = os.path.join('//', asset_name)

        counter = 0
        while os.path.isfile(f'{thumb_path}.jpg'):
            new_name = f'{asset_name}_{str(counter).zfill(4)}'
            thumb_path = os.path.join(file_dir, new_name)
            self.rel_thumb_path = os.path.join('//', new_name)
            counter += 1

        _common_setup(self.props, asset_name, 'model', json_data, thumb_path, self._done_callback)


class GenerateMaterialThumbnailOperator(bpy.types.Operator):
    """Generate Cycles thumbnail for materials."""

    bl_idname = f'material.{HANA3D_NAME}_thumbnail'
    bl_label = f'{HANA3D_DESCRIPTION} Material Thumbnail Generator'
    bl_options = {'REGISTER', 'INTERNAL'}

    @classmethod
    def poll(cls, context):
        """Material thumbnailer poll.

        Parameters:
            context: Blender context

        Returns:
            bool: if there is an active object
        """
        return bpy.context.view_layer.objects.active is not None

    def draw(self, context):    # noqa: WPS213
        """Material thumbnailer draw.

        Parameters:
            context: Blender context
        """
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
        layout.prop(preferences, 'thumbnail_use_gpu')

    @execute_wrapper
    def execute(self, context):
        """Material thumbnailer execute.

        Parameters:
            context: Blender context

        Returns:
            enum set in {‘RUNNING_MODAL’, ‘CANCELLED’, ‘FINISHED’, ‘PASS_THROUGH’, ‘INTERFACE’}
        """
        try:    # noqa: WPS229
            material = utils.get_active_material(context)
            self.props = getattr(material, HANA3D_NAME)
            self._generate_material_thumbnail(material)
        except Exception as error:
            props.is_generating_thumbnail = False
            props.thumbnail_generating_state = ''
            logging.warning(f'Error while packing file: {str(error)}')
            return {'CANCELLED'}
        return {'FINISHED'}

    def invoke(self, context, event):
        """Material thumbnailer invoke.

        Parameters:
            context: Blender context
            event: invoker event

        Returns:
            enum set in {‘RUNNING_MODAL’, ‘CANCELLED’, ‘FINISHED’, ‘PASS_THROUGH’, ‘INTERFACE’}
        """
        wm = context.window_manager
        if bpy.data.filepath == '':
            title = 'Cannot render thumbnail'
            message = 'please save your file first'
            utils.show_pop_menu(message, title)

            return {'CANCELLED'}

        return wm.invoke_props_dialog(self)

    def _done_callback(self, task):
        self.props.thumbnail = f'{self.rel_thumb_path}.jpg'
        self.props.thumbnail_generating_state = 'rendering done'
        self.props.is_generating_thumbnail = False

        if bpy.data.use_autopack is True:
            bpy.ops.file.autopack_toggle()

    def _generate_material_thumbnail(   # noqa: WPS210
        self,
        material: bpy.types.Material,
        asset_name: str = None,
        save_only: bool = False,
        blend_filepath: str = '',
    ):
        if asset_name is None:
            asset_name = material.name

        json_data = {
            'type': 'material',
            'material': material.name,
            'thumbnail_type': self.props.thumbnail_generator_type,
            'thumbnail_scale': self.props.thumbnail_scale,
            'thumbnail_background': self.props.thumbnail_background,
            'thumbnail_background_lightness': self.props.thumbnail_background_lightness,
            'thumbnail_resolution': self.props.thumbnail_resolution,
            'thumbnail_samples': self.props.thumbnail_samples,
            'thumbnail_denoising': self.props.thumbnail_denoising,
            'adaptive_subdivision': self.props.adaptive_subdivision,
            'texture_size_meters': self.props.texture_size_meters,
            'save_only': save_only,
            'blend_filepath': blend_filepath,
        }

        file_dir = os.path.dirname(bpy.data.filepath)
        thumb_path = os.path.join(file_dir, asset_name)
        self.rel_thumb_path = os.path.join('//', asset_name)

        counter = 0
        while os.path.isfile(f'{thumb_path}.jpg'):
            new_name = f'{asset_name}_{str(counter).zfill(4)}'
            thumb_path = os.path.join(file_dir, new_name)
            self.rel_thumb_path = os.path.join('//', new_name)
            counter += 1

        _common_setup(
            self.props,
            asset_name,
            'material',
            json_data,
            thumb_path,
            self._done_callback,
        )


class GenerateSceneThumbnailOperator(bpy.types.Operator):
    """Generate Cycles thumbnail for scene."""

    bl_idname = f'scene.{HANA3D_NAME}_thumbnail'
    bl_label = f'{HANA3D_DESCRIPTION} Thumbnail Generator'
    bl_options = {'REGISTER', 'INTERNAL'}

    @classmethod
    def poll(cls, context):
        """Scene thumbnailer poll.

        Parameters:
            context: Blender context

        Returns:
            bool: if there is an active object
        """
        return bpy.context.view_layer.objects.active is not None

    def draw(self, context):
        """Scene thumbnailer draw.

        Parameters:
            context: Blender context
        """
        ob = context.active_object
        while ob.parent is not None:
            ob = ob.parent
        props = getattr(ob, HANA3D_NAME)
        layout = self.layout
        layout.label(text='thumbnailer settings')
        layout.prop(props, 'thumbnail_samples')
        layout.prop(props, 'thumbnail_resolution')
        layout.prop(props, 'thumbnail_denoising')
        preferences = context.preferences.addons[HANA3D_NAME].preferences
        layout.prop(preferences, 'thumbnail_use_gpu')

    @execute_wrapper
    def execute(self, context):
        """Scene thumbnailer execute.

        Parameters:
            context: Blender context

        Returns:
            enum set in {‘RUNNING_MODAL’, ‘CANCELLED’, ‘FINISHED’, ‘PASS_THROUGH’, ‘INTERFACE’}
        """
        try:    # noqa: WPS229
            props = getattr(self._get_active_scene(context), HANA3D_NAME)
            self._generate_scene_thumbnail(props)
        except Exception as error:
            logging.warning(f'Error while exporting file: {str(error)}')
            return {'CANCELLED'}
        finally:
            props.thumbnail_generating_state = 'Finished'
            props.is_generating_thumbnail = False
        return {'FINISHED'}

    def invoke(self, context, event):
        """Scene thumbnailer invoke.

        Parameters:
            context: Blender context
            event: invoke event

        Returns:
            enum set in {‘RUNNING_MODAL’, ‘CANCELLED’, ‘FINISHED’, ‘PASS_THROUGH’, ‘INTERFACE’}
        """
        wm = context.window_manager
        if bpy.data.filepath == '':
            title = 'Cannot render thumbnail'
            message = 'please save your file first'
            utils.show_pop_menu(message, title)

            return {'CANCELLED'}

        return wm.invoke_props_dialog(self)

    def _get_active_scene(self, context=None, view_id: str = None):
        context = context or bpy.context
        if view_id is None:
            return context.scene
        scenes = [scene for scene in context.blend_data.scenes if scene.view_id == view_id]

        return scenes[0]

    def _generate_scene_thumbnail(  # noqa: WPS210
        self,
        props=None,
        save_only: bool = False,
        blend_filepath: str = '',
    ):
        context = bpy.context
        props.is_generating_thumbnail = True
        props.thumbnail_generating_state = 'starting blender instance'

        basename, ext = os.path.splitext(bpy.data.filepath)
        if not basename:
            basename = os.path.join(basename, 'temp')
        if not ext:
            ext = '.blend'

        asset_name = os.path.basename(basename)
        file_dir = os.path.dirname(bpy.data.filepath)
        thumb_path = os.path.join(file_dir, asset_name)
        rel_thumb_path = os.path.join('//', asset_name)

        counter = 0
        while os.path.isfile(f'{thumb_path}.png'):
            new_name = f'{asset_name}_{str(counter).zfill(4)}'
            thumb_path = os.path.join(file_dir, new_name)
            self.rel_thumb_path = os.path.join('//', new_name)
            counter += 1

        user_preferences = context.preferences.addons[HANA3D_NAME].preferences

        if user_preferences.thumbnail_use_gpu:
            context.scene.cycles.device = 'GPU'

        context.scene.cycles.samples = props.thumbnail_samples
        context.view_layer.cycles.use_denoising = props.thumbnail_denoising

        resolution_x = context.scene.render.resolution_x
        resolution_y = context.scene.render.resolution_y

        context.scene.render.resolution_x = int(props.thumbnail_resolution)
        context.scene.render.resolution_y = int(props.thumbnail_resolution)

        if save_only:
            bpy.ops.wm.save_as_mainfile(filepath=blend_filepath, compress=True, copy=True)
        else:
            context.scene.render.filepath = f'{thumb_path}.png'
            bpy.ops.render.render(write_still=True, animation=False)
            props.thumbnail = f'{rel_thumb_path}.png'

        context.scene.render.resolution_x = resolution_x
        context.scene.render.resolution_y = resolution_y


classes = (
    GenerateModelThumbnailOperator,
    GenerateMaterialThumbnailOperator,
    GenerateSceneThumbnailOperator,
)


def register():
    """Autothumb register."""
    for class_ in classes:
        bpy.utils.register_class(class_)


def unregister():
    """Autothumb unregister."""
    for class_ in reversed(classes):
        bpy.utils.unregister_class(class_)
