"""Blender script to render material thumbnail."""
import json
import logging
import sys
from importlib import import_module
from pathlib import Path

import bpy

HANA3D_NAME = sys.argv[-1]
HANA3D_EXPORT_TEMP_DIR = sys.argv[-2]
HANA3D_THUMBNAIL_PATH = sys.argv[-3]
HANA3D_EXPORT_FILE_INPUT = sys.argv[-4]
HANA3D_EXPORT_DATA = sys.argv[-5]

module = import_module(HANA3D_NAME)
append_link = module.append_link
utils = module.utils


def _unhide_collection(cname, context):
    collection = context.scene.collection.children[cname]
    collection.hide_viewport = False
    collection.hide_render = False
    collection.hide_select = False


if __name__ == "__main__":
    try:
        with open(HANA3D_EXPORT_DATA, 'r') as file_:
            data = json.load(file_)
        link = not data['save_only']

        mat = append_link.append_material(
            file_name=HANA3D_EXPORT_FILE_INPUT,
            matname=data["material"],
            link=link,
            fake_user=False
        )

        user_preferences = bpy.context.preferences.addons[HANA3D_NAME].preferences

        context = bpy.context
        scene = context.scene

        colmapdict = {
            'BALL': 'Ball',
            'CUBE': 'Cube',
            'FLUID': 'Fluid',
            'CLOTH': 'Cloth',
            'HAIR': 'Hair',
        }

        _unhide_collection(colmapdict[data["thumbnail_type"]], context)
        if data['thumbnail_background']:
            _unhide_collection('Background', context)
            bpy.data.materials["bg checker colorable"].node_tree.nodes['input_level'].outputs[
                'Value'
            ].default_value = data['thumbnail_background_lightness']
        tscale = data["thumbnail_scale"]
        bpy.context.view_layer.objects['scaler'].scale = (tscale, tscale, tscale)
        bpy.context.view_layer.update()
        for ob in bpy.context.visible_objects:
            if ob.name[:15] == 'MaterialPreview':
                ob.material_slots[0].material = mat
                ob.data.texspace_size.x = 1 / tscale
                ob.data.texspace_size.y = 1 / tscale
                ob.data.texspace_size.z = 1 / tscale
                if data["adaptive_subdivision"]:
                    ob.cycles.use_adaptive_subdivision = True
                else:
                    ob.cycles.use_adaptive_subdivision = False
                tex_size = data['texture_size_meters']
                if data["thumbnail_type"] in ['BALL', 'CUBE', 'CLOTH']:
                    utils.automap(
                        ob.name,
                        tex_size=tex_size / tscale,
                        just_scale=True,
                        bg_exception=True
                    )
        context.view_layer.update()

        scene.cycles.volume_step_size = tscale * 0.1

        if user_preferences.thumbnail_use_gpu:
            context.scene.cycles.device = 'GPU'

        scene.cycles.samples = data['thumbnail_samples']
        context.view_layer.cycles.use_denoising = data['thumbnail_denoising']

        # import blender's HDR here
        hdr_path = Path('datafiles/studiolights/world/interior.exr')
        bpath = Path(bpy.utils.resource_path('LOCAL'))
        ipath = bpath / hdr_path
        ipath = str(ipath)

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

    except Exception as e:
        logging.error(e)
        import traceback

        traceback.print_exc()

        sys.exit(1)
