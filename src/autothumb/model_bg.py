"""Blender script to render model thumbnail."""
import ast
import json
import logging
import math
import sys
import traceback
from importlib import import_module
from pathlib import Path

import bpy
import mathutils

HANA3D_NAME = sys.argv[-1]
HANA3D_EXPORT_TEMP_DIR = sys.argv[-2]
HANA3D_THUMBNAIL_PATH = sys.argv[-3]
HANA3D_EXPORT_FILE_INPUT = sys.argv[-4]
HANA3D_EXPORT_DATA = sys.argv[-5]

module = import_module(HANA3D_NAME)
append_link = module.append_link
utils = module.utils


def _get_obnames():
    with open(HANA3D_EXPORT_DATA, 'r') as data_file:
        model_data = json.load(data_file)
    return ast.literal_eval(model_data['models'])


def _center_obs_for_thumbnail(obs):  # noqa: WPS210
    scene = bpy.context.scene
    parent = obs[0]

    while parent.parent is not None:
        parent = parent.parent
    # reset parent rotation, so we see how it really snaps.
    parent.rotation_euler = (0, 0, 0)
    bpy.context.view_layer.update()
    minx, miny, minz, maxx, maxy, maxz = utils.get_bounds_worldspace(obs)

    cx = (maxx - minx) / 2 + minx
    cy = (maxy - miny) / 2 + miny
    for ob in scene.collection.objects:
        ob.select_set(False)

    bpy.context.view_layer.objects.active = parent
    parent.location += mathutils.Vector((-cx, -cy, -minz))

    cam_z = scene.camera.parent.parent
    cam_z.location.z = (maxz - minz) / 2    # noqa: WPS111
    dx = maxx - minx
    dy = maxy - miny
    dz = maxz - minz
    scale_factor = math.sqrt(dx * dx + dy * dy + dz * dz)   # noqa: WPS221

    scaler = bpy.context.view_layer.objects['scaler']
    scaler.scale = (scale_factor, scale_factor, scale_factor)
    coef = 0.7
    scale_factor *= coef
    cam_z.scale = (scale_factor, scale_factor, scale_factor)
    bpy.context.view_layer.update()


if __name__ == '__main__':
    try:    # noqa: WPS229
        logging.info('autothumb_model_bg')
        with open(HANA3D_EXPORT_DATA, 'r') as data_file:
            data = json.load(data_file)  # noqa: WPS110

        context = bpy.context
        scene = context.scene

        user_preferences = context.preferences.addons[HANA3D_NAME].preferences

        obnames = _get_obnames()
        link = not data['save_only']
        main_object, allobs = append_link.append_objects(
            file_name=HANA3D_EXPORT_FILE_INPUT,
            obnames=obnames,
            link=link,
        )
        context.view_layer.update()

        camdict = {
            'GROUND': 'camera ground',
            'WALL': 'camera wall',
            'CEILING': 'camera ceiling',
            'FLOAT': 'camera float',
        }

        context.scene.camera = bpy.data.objects[camdict[data['thumbnail_snap_to']]]
        _center_obs_for_thumbnail(allobs)
        if user_preferences.thumbnail_use_gpu:
            context.scene.cycles.device = 'GPU'

        fdict = {
            'DEFAULT': 1,
            'FRONT': 2,
            'SIDE': 3,
            'TOP': 4,
        }
        scene.frame_set(fdict[data['thumbnail_angle']])

        snapdict = {'GROUND': 'Ground', 'WALL': 'Wall', 'CEILING': 'Ceiling', 'FLOAT': 'Float'}

        collection = context.scene.collection.children[snapdict[data['thumbnail_snap_to']]]
        collection.hide_viewport = False
        collection.hide_render = False
        collection.hide_select = False

        main_object.rotation_euler = (0, 0, 0)
        # material declared on thumbnailer.blend
        node_tree = bpy.data.materials['hana3d background'].node_tree
        value_output = node_tree.nodes['Value'].outputs['Value']
        value_output.default_value = data['thumbnail_background_lightness']
        scene.cycles.samples = data['thumbnail_samples']
        context.view_layer.cycles.use_denoising = data['thumbnail_denoising']
        context.view_layer.update()

        # import blender's HDR here
        hdr_path = Path('datafiles/studiolights/world/interior.exr')
        bpath = Path(bpy.utils.resource_path('LOCAL'))
        ipath = str(bpath / hdr_path)

        # this  stuff is for mac and possibly linux. For blender // means relative path.
        # for Mac, // means start of absolute path
        if ipath.startswith('//'):
            ipath = ipath[1:]

        hdr_img = bpy.data.images['interior.exr']
        hdr_img.filepath = ipath
        hdr_img.reload()

        context.scene.render.resolution_x = int(data['thumbnail_resolution'])
        context.scene.render.resolution_y = int(data['thumbnail_resolution'])

        if data['save_only']:
            hdr_img.pack()
            bpy.ops.wm.save_as_mainfile(filepath=data['blend_filepath'], compress=True, copy=True)
        else:
            context.scene.render.filepath = HANA3D_THUMBNAIL_PATH
            bpy.ops.render.render(write_still=True, animation=False)

    except Exception as error:
        logging.error(error)

        traceback.print_exc()
        sys.exit(1)
