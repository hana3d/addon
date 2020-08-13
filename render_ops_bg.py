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
    bg_blender = reload(bg_blender)
    utils = reload(utils)
    rerequests = reload(rerequests)
else:
    from hana3d import paths, bg_blender, utils, rerequests

import json
import os
import sys
import time
import uuid
from typing import Tuple

import bpy
import requests

HANA3D_EXPORT_DATA = sys.argv[-1]


def create_render_view(
        asset_id: str,
        view_id: str,
        filepath: str,
        headers: dict,
) -> Tuple[str, str]:
    url = paths.get_api_url('uploads')
    data = {
        'assetId': asset_id,
        'originalFilename': os.path.basename(filepath),
        'id_parent': view_id,
        'metadata': {'is_render_scene': True},
    }
    response = rerequests.post(url, json=data, headers=headers)
    assert response.ok, response.text

    dict_response = response.json()

    render_scene_id = dict_response['id']
    upload_url = dict_response['s3UploadUrl']
    return render_scene_id, upload_url


def upload_file(filepath: str, upload_url: str, headers: dict):
    chunk_size = 2 * 1024 * 1024
    try:
        # TODO: Multipart upload
        upload_response = requests.put(
            upload_url,
            data=utils.upload_in_chunks(filepath, chunk_size, report_name='blend'),
            stream=True,
        )
        assert upload_response.ok
    except Exception as e:
        print(e)
        bg_blender.progress('Upload failed.')
        return
    bg_blender.progress('Upload complete')


def confirm_file_upload(render_scene_id: str, headers: dict):
    url = paths.get_api_url('uploads_s3', render_scene_id, 'upload-file')
    rerequests.post(url, headers=headers)


def create_job(
        render_scene_id: str,
        engine: str,
        frame_start: int,
        frame_end: int,
        headers: dict) -> str:
    bg_blender.progress('Creating Job')
    job_url = paths.get_api_url('render_jobs')

    data = {
        'render_scene_id': render_scene_id,
        'engine': engine,
        'frame_start': frame_start,
        'frame_end': frame_end,
    }
    response = rerequests.post(job_url, json=data, headers=headers)
    job = response.json()
    return job['id']


def pool_job(job_id: str, headers: dict, pool_time: int = 5) -> str:
    while True:
        url = paths.get_api_url('render_jobs', job_id)
        response = rerequests.get(url, headers=headers)
        job = response.json()
        if job['status'] == 'FINISHED':
            bg_blender.progress('Job complete')
            break
        elif job['status'] == 'CANCELED':
            bg_blender.progress('Job cancelled')
            break
        elif job['status'] == 'ERRORED':
            bg_blender.progress('Error in job')
            break
        else:
            bg_blender.progress('Job progress: ', job['progress'] * 100)
            time.sleep(pool_time)
    return job['output_url']


if __name__ == "__main__":
    try:
        render_props = bpy.context.scene.Hana3DRender
        render_props.rendering = True

        with open(HANA3D_EXPORT_DATA, 'r') as s:
            data = json.load(s)
        bpy.app.debug_value = data.get('debug_value', 0)
        asset_id = data['asset_id']
        view_id = data['view_id']
        engine = data['engine']
        frame_start = data['frame_start']
        frame_end = data['frame_end']
        filepath = data['filepath']

        correlation_id = str(uuid.uuid4())
        headers = utils.get_headers(correlation_id)

        render_scene_id, upload_url = create_render_view(asset_id, view_id, filepath, headers)
        upload_file(filepath, upload_url, headers)
        confirm_file_upload(render_scene_id, headers)
        job_id = create_job(render_scene_id, engine, frame_start, frame_end, headers)
        render = pool_job(job_id, headers)

        # TODO: improve bring-result-to-scene
        bpy.context.scene.Hana3DRender.render_path = render
        bg_blender.progress('Job finished successfully')

    except Exception as e:
        bg_blender.progress(e)
        print(e)
        sys.exit(1)
