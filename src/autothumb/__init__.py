"""Automatic thumbnailer."""
import logging

import bpy

from ... import colors, ui, utils
from ...config import HANA3D_DESCRIPTION, HANA3D_NAME
from ...report_tools import execute_wrapper
from .autothumb import (
    generate_material_thumbnail,
    generate_model_thumbnail,
    generate_scene_thumbnail,
)

HANA3D_EXPORT_DATA_FILE = f"{HANA3D_NAME}_data.json"


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
            props = getattr(utils.get_active_model(context), HANA3D_NAME)
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
            props = getattr(utils.get_active_material(context), HANA3D_NAME)
            generate_material_thumbnail(props)
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

    @execute_wrapper
    def execute(self, context):
        try:
            props = getattr(get_active_scene(context), HANA3D_NAME)
            generate_scene_thumbnail(props)
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
