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


def register():
    bpy.utils.register_class(GenerateMaterialThumbnailOperator)


def unregister():
    bpy.utils.unregister_class(GenerateMaterialThumbnailOperator)
