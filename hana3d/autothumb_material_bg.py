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
bg_blender = module.bg_blender
utils = module.utils


def unhide_collection(cname):
    collection = bpy.context.scene.collection.children[cname]
    collection.hide_viewport = False
    collection.hide_render = False
    collection.hide_select = False


if __name__ == "__main__":
    try:
        bg_blender.progress('preparing thumbnail scene')
        with open(HANA3D_EXPORT_DATA, 'r') as s:
            data = json.load(s)
            # append_material(file_name, matname = None, link = False, fake_user = True)
        link = not data['save_only']

        mat = append_link.append_material(
            file_name=HANA3D_EXPORT_FILE_INPUT,
            matname=data["material"],
            link=link,
            fake_user=False
        )

        user_preferences = bpy.context.preferences.addons[HANA3D_NAME].preferences

        s = bpy.context.scene

        colmapdict = {
            'BALL': 'Ball',
            'CUBE': 'Cube',
            'FLUID': 'Fluid',
            'CLOTH': 'Cloth',
            'HAIR': 'Hair',
        }

        unhide_collection(colmapdict[data["thumbnail_type"]])
        if data['thumbnail_background']:
            unhide_collection('Background')
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
                ts = data['texture_size_meters']
                if data["thumbnail_type"] in ['BALL', 'CUBE', 'CLOTH']:
                    utils.automap(ob.name, tex_size=ts / tscale, just_scale=True, bg_exception=True)
        bpy.context.view_layer.update()

        s.cycles.volume_step_size = tscale * 0.1

        if user_preferences.thumbnail_use_gpu:
            bpy.context.scene.cycles.device = 'GPU'

        s.cycles.samples = data['thumbnail_samples']
        bpy.context.view_layer.cycles.use_denoising = data['thumbnail_denoising']

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

        bpy.context.scene.render.resolution_x = int(data['thumbnail_resolution'])
        bpy.context.scene.render.resolution_y = int(data['thumbnail_resolution'])

        if data['save_only']:
            hdr_img.pack()
            bpy.ops.wm.save_as_mainfile(filepath=data['blend_filepath'], compress=True, copy=True)
        else:
            bpy.context.scene.render.filepath = HANA3D_THUMBNAIL_PATH
            bg_blender.progress('rendering thumbnail')
            bpy.ops.render.render(write_still=True, animation=False)
        bg_blender.progress('background autothumbnailer finished successfully')

    except Exception as e:
        logging.error(e)
        import traceback

        traceback.print_exc()

        sys.exit(1)
