import json
import logging
import os
import sys
from importlib import import_module

import bpy

FILENAME = sys.argv[-1]
HANA3D_NAME = sys.argv[-2]
HANA3D_EXPORT_DATA = sys.argv[-3]

module = import_module(HANA3D_NAME)
append_link = module.append_link
utils = module.utils


def get_parent_object():
    obj = bpy.context.scene.objects[0]
    while obj.parent is not None:
        obj = obj.parent
    return obj


def set_origin_zero(coll):
    parent = get_parent_object()
    if parent.type == 'EMPTY':
        parent.select_set(True)
        bpy.ops.object.transform_apply()

        list_children = list(parent.children)
        for child in parent.children:
            child.parent = None
        parent.location = (0, 0, 0)

        for child in list_children:
            child.parent = parent
    else:
        bpy.context.view_layer.objects.active = parent
        parent.select_set(True)

        bpy.ops.object.origin_set(type='ORIGIN_CURSOR')


def fix_objects_origin(objects, coll):
    """Move a group of objects to the center of the XY plane at height zero.
    Origin of parent object is set to (0, 0, 0)"""
    utils.centralize(objects)
    set_origin_zero(coll)


if __name__ == "__main__":
    try:
        with open(HANA3D_EXPORT_DATA, 'r') as s:
            data = json.load(s)

        export_data = data['export_data']
        upload_data = data['upload_data']
        correlation_id = data['correlation_id']

        bpy.data.scenes.new('upload')
        for s in bpy.data.scenes:
            if s.name != 'upload':
                bpy.data.scenes.remove(s)

        if export_data['type'] == 'MODEL':
            obnames = export_data['models']
            main_source, allobs = append_link.append_objects(
                file_name=data['source_filepath'],
                obnames=obnames,
                rotation=(0, 0, 0)
            )
            g = bpy.data.collections.new(upload_data['name'])
            for o in allobs:
                g.objects.link(o)
            bpy.context.scene.collection.children.link(g)
            fix_objects_origin(allobs, g)
        elif export_data['type'] == 'SCENE':
            sname = export_data['scene']
            main_source = append_link.append_scene(
                file_name=data['source_filepath'],
                scenename=sname
            )
            bpy.data.scenes.remove(bpy.data.scenes['upload'])
            main_source.name = sname
        elif export_data['type'] == 'MATERIAL':
            matname = export_data['material']
            main_source = append_link.append_material(
                file_name=data['source_filepath'],
                matname=matname
            )

        bpy.ops.file.pack_all()

        main_source_props = getattr(main_source, HANA3D_NAME)
        main_source_props.uploading = False
        fpath = os.path.join(data['temp_dir'], FILENAME)

        bpy.ops.wm.save_as_mainfile(filepath=fpath, compress=True, copy=False)
        os.remove(data['source_filepath'])

    except Exception as e:
        logging.exception(e)
        sys.exit(1)
