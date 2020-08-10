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

import bpy
import requests

HANA3D_EXPORT_DATA = sys.argv[-1]


class upload_in_chunks(object):
    def __init__(self, filename, chunksize=1 << 13, report_name='file'):
        self.filename = filename
        self.chunksize = chunksize
        self.totalsize = os.path.getsize(filename)
        self.readsofar = 0
        self.report_name = report_name

    def __iter__(self):
        with open(self.filename, 'rb') as file:
            while True:
                data = file.read(self.chunksize)
                if not data:
                    sys.stderr.write("\n")
                    break
                self.readsofar += len(data)
                percent = self.readsofar * 1e2 / self.totalsize
                bg_blender.progress('uploading %s' % self.report_name, percent)
                yield data

    def __len__(self):
        return self.totalsize


def upload_file(filepath):
    bpy.app.debug_value = data.get('debug_value', 0)

    headers = utils.get_headers()

    upload_create_url = paths.get_render_farm_upload_url()
    upload = rerequests.get(upload_create_url, headers=headers, verify=True)
    upload = upload.json()
    chunk_size = 1024 * 1024 * 2
    uploaded = False
    for a in range(0, 5):
        if not uploaded:
            try:
                upload_response = requests.put(
                    upload['uploadUrls'][0],  # TODO: Change to multiparts
                    data=upload_in_chunks(filepath, chunk_size, "blend"),
                    stream=True,
                    verify=True,
                )

                if upload_response.status_code == 200:
                    uploaded = True
                else:
                    print(upload_response.text)
                    bg_blender.progress(f'Upload failed, retry. {a}')
            except Exception as e:
                print(e)
                bg_blender.progress('Upload .blend failed, retrying')
                time.sleep(1)
    if not uploaded:
        bg_blender.progress('Upload failed.')
        return None
    bg_blender.progress('Upload complete')
    return upload['url']


def create_project(name: str, url: str, file_size: int, user_id: str):
    headers = utils.get_headers()
    bg_blender.progress('Creating Project')
    project_url = paths.get_render_farm_project_url(user_id)

    data = {
        'name': name,
        'url': url,
        'sizeBytes': file_size
    }
    project = rerequests.post(project_url, json=data, headers=headers, verify=True)
    project = project.json()

    return project['id']


def create_job(project_id: str, engine: str, frame_start: int, frame_end: int):
    headers = utils.get_headers()
    bg_blender.progress('Creating Job')
    job_url = paths.get_render_farm_job_url(project_id)

    data = {
        'engine': engine,
        'frameStart': frame_start,
        'frameEnd': frame_end
    }

    job = rerequests.post(job_url, json=data, headers=headers, verify=True)
    job = job.json()

    return job['id']


def start_job(job_id: str):
    headers = utils.get_headers()
    bg_blender.progress('Starting Job')
    job_url = paths.get_render_farm_job_start_url(job_id)
    rerequests.post(job_url, headers=headers, verify=True)


def pool_job(user_id: str, job_id: str):
    complete = False
    while not complete:
        headers = utils.get_headers()
        job_url = paths.get_render_farm_job_get_url(user_id, job_id)
        job = rerequests.get(job_url, headers=headers, verify=True)
        job = job.json()[0]
        if job['status'] == 'FINISHED':
            complete = True
            bg_blender.progress('Job complete')
        elif job['status'] == 'CANCELED':
            complete = True
            bg_blender.progress('Job cancelled')
        elif job['status'] == 'ERRORED':
            complete = True
            bg_blender.progress('Error in job')
        else:
            bg_blender.progress('Job progress: ', job['progress'])
            time.sleep(1)
    return job['output'][0]


if __name__ == "__main__":
    try:
        render_props = bpy.context.scene.Hana3DRender
        render_props.rendering = True

        with open(HANA3D_EXPORT_DATA, 'r') as s:
            data = json.load(s)
        name = data['asset'] + '.blend'
        filepath = data['source_filepath']
        user_id = data['user_id']
        engine = data['engine']
        frame_start = data['frame_start']
        frame_end = data['frame_end']
        file_size = os.path.getsize(filepath)

        url = upload_file(filepath)
        project_id = create_project(name, url, file_size, user_id)
        job_id = create_job(project_id, engine, frame_start, frame_end)
        start_job(job_id)
        render = pool_job(user_id, job_id)
        # TODO: improve bring-result-to-scene
        bpy.context.scene.Hana3DRender.render_path = render
        bg_blender.progress('Job finished successfully')

    except Exception as e:
        bg_blender.progress(e)
        print(e)
        sys.exit(1)
