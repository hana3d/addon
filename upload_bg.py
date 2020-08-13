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


if "bpy" in locals():
    from importlib import reload

    paths = reload(paths)
    append_link = reload(append_link)
    bg_blender = reload(bg_blender)
    utils = reload(utils)
    rerequests = reload(rerequests)
else:
    from hana3d import paths, append_link, bg_blender, utils, rerequests

import json
import logging
import os
import sys
import time

import bpy
import requests

HANA3D_EXPORT_DATA = sys.argv[-1]


def start_logging():
    logging.basicConfig()
    logging.getLogger().setLevel(logging.DEBUG)
    requests_log = logging.getLogger("requests.packages.urllib3")
    requests_log.setLevel(logging.DEBUG)
    requests_log.propagate = True


def print_gap():
    print('\n\n\n\n')


def upload_file(upload_data, f, correlation_id):
    headers = utils.get_headers(correlation_id)
    bg_blender.progress('uploading %s' % f['type'])
    upload_info = {
        'assetId': upload_data['id'],
        'fileType': f['type'],
        'fileIndex': f['index'],
        'originalFilename': os.path.basename(f['file_path']),
        'comment': f['publish_message']
    }
    if f['type'] == 'blend':
        upload_info['viewId'] = upload_data['viewId']
    upload_create_url = paths.get_api_url('uploads')
    response = rerequests.post(upload_create_url, json=upload_info, headers=headers)
    upload = response.json()
    #
    chunk_size = 1024 * 1024 * 2
    utils.pprint(upload)
    # file gets uploaded here:
    uploaded = False
    # s3 upload is now the only option
    for a in range(0, 5):
        if not uploaded:
            try:
                upload_response = requests.put(
                    upload['s3UploadUrl'],
                    data=utils.upload_in_chunks(f['file_path'], chunk_size, f['type']),
                    stream=True,
                )

                if upload_response.status_code == 200:
                    uploaded = True
                else:
                    print(upload_response.text)
                    bg_blender.progress(f'Upload failed, retry. {a}')
            except Exception as e:
                print(e)
                bg_blender.progress('Upload %s failed, retrying' % f['type'])
                time.sleep(1)

            # confirm single file upload to hana3d server
            upload_done_url = paths.get_api_url('uploads_s3', upload['id'], 'upload-file')
            upload_response = rerequests.post(upload_done_url, headers=headers)

    bg_blender.progress('finished uploading')

    return uploaded


def upload_files(upload_data, files, correlation_id):
    uploaded_all = True
    for f in files:
        uploaded = upload_file(upload_data, f, correlation_id)
        if not uploaded:
            uploaded_all = False
        bg_blender.progress('finished uploading')
    return uploaded_all


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
        bg_blender.progress('preparing scene - append data')
        with open(HANA3D_EXPORT_DATA, 'r') as s:
            data = json.load(s)

        bpy.app.debug_value = data.get('debug_value', 0)
        export_data = data['export_data']
        upload_data = data['upload_data']
        correlation_id = data['correlation_id']

        upload_set = data['upload_set']
        if 'MAINFILE' in upload_set:
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
            if export_data['type'] == 'SCENE':
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

            main_source.hana3d.uploading = False
            fpath = os.path.join(data['temp_dir'], upload_data['viewId'] + '.blend')

            bpy.ops.wm.save_as_mainfile(filepath=fpath, compress=True, copy=False)
            os.remove(data['source_filepath'])

        bg_blender.progress('preparing scene - open files')

        files = []
        if 'THUMBNAIL' in upload_set:
            files.append(
                {
                    "type": "thumbnail",
                    "index": 0,
                    "file_path": export_data["thumbnail_path"],
                    "publish_message": None
                }
            )
        if 'MAINFILE' in upload_set:
            files.append(
                {
                    "type": "blend",
                    "index": 0,
                    "file_path": fpath,
                    "publish_message": export_data['publish_message']
                }
            )

        bg_blender.progress('uploading')

        uploaded = upload_files(upload_data, files, correlation_id)

        if uploaded:
            # mark on server as uploaded
            if 'MAINFILE' in upload_set:
                confirm_data = {"verificationStatus": "uploaded"}

                url = paths.get_api_url('assets', upload_data['id'])
                headers = utils.get_headers(correlation_id)
                rerequests.patch(url, json=confirm_data, headers=headers)

            bg_blender.progress('upload finished successfully')
        else:
            bg_blender.progress('upload failed.')

    except Exception as e:
        print(e)
        bg_blender.progress(e)
        sys.exit(1)
