"""Create background processes."""
import json
import os
import tempfile

import bpy

from ... import paths, utils
from ...config import HANA3D_NAME
from ..async_loop import run_async_function
from ..subprocess_async.subprocess_async import Subprocess

HANA3D_EXPORT_DATA_FILE = f"{HANA3D_NAME}_data.json"


def _common_setup(props, asset_name: str, asset_type: str, json_data: dict):
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

    file_dir = os.path.dirname(bpy.data.filepath)
    thumb_path = os.path.join(file_dir, asset_name)
    rel_thumb_path = os.path.join('//', asset_name)

    i = 0
    while os.path.isfile(thumb_path + '.jpg'):
        thumb_path = os.path.join(file_dir, asset_name + '_' + str(i).zfill(4))
        rel_thumb_path = os.path.join('//', asset_name + '_' + str(i).zfill(4))
        i += 1

    filepath = os.path.join(tempdir, "thumbnailer_" + HANA3D_NAME + ext)
    tfpath = paths.get_thumbnailer_filepath(asset_type)
    datafile = os.path.join(tempdir, HANA3D_EXPORT_DATA_FILE)

    autopack = False
    if bpy.data.use_autopack is True:
        autopack = True
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
    run_async_function(subprocess.subprocess, cmd=cmd)

    props.thumbnail = rel_thumb_path + '.jpg'
    props.thumbnail_generating_state = 'Saving .blend file'

    if autopack is True:
        bpy.ops.file.autopack_toggle()


def generate_model_thumbnail(
        props=None,
        asset_name: str = None,
        save_only: bool = False,
        blend_filepath: str = ''):
    if props is None:
        props = getattr(bpy.data.objects[asset_name], HANA3D_NAME)
    mainmodel = utils.get_active_model()
    model_props = getattr(mainmodel, HANA3D_NAME)
    assert model_props.view_id == props.view_id, 'Error when checking for active asset'
    if asset_name is None:
        asset_name = mainmodel.name

    obs = utils.get_hierarchy(mainmodel)
    obnames = []
    for ob in obs:
        obnames.append(ob.name)

    json_data = {
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
    }

    _common_setup(model_props, asset_name, 'model', json_data)


def generate_material_thumbnail(
        props=None,
        asset_name: str = None,
        save_only: bool = False,
        blend_filepath: str = ''):
    if props is None:
        props = getattr(bpy.data.materials[asset_name], HANA3D_NAME)
    mat = utils.get_active_material()
    material_props = getattr(mat, HANA3D_NAME)
    assert material_props.view_id == props.view_id, 'Error when checking active material'
    if asset_name is None:
        asset_name = mat.name

    json_data = {
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
    }

    _common_setup(material_props, asset_name, 'material', json_data)


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
