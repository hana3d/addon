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

if 'bpy' in locals():
    from importlib import reload

    colors = reload(colors)
    paths = reload(paths)
    rerequests = reload(rerequests)
    types = reload(types)
    ui = reload(ui)
    utils = reload(utils)
else:
    from hana3d import colors, paths, rerequests, types, ui, utils

import os
import shutil
import tempfile
import threading
import time
import uuid
from collections import defaultdict
from copy import copy
from datetime import datetime
from typing import Tuple

import bpy
import bpy.utils.previews
import requests
from bpy.props import BoolProperty, CollectionProperty, StringProperty
from bpy.types import Operator
from bpy_extras.image_utils import load_image

render_threads = []
upload_threads = []


def threads_timer():
    '''Cleanup finished threads'''
    if len(render_threads) == 0:
        return 10

    for thread in copy(render_threads):
        if thread.is_alive():
            continue
        if not thread.finished:
            # Implement retry logic here
            pass
        shutil.rmtree(thread.tempdir, ignore_errors=True)
        render_threads.remove(thread)

    for thread_list in copy(upload_threads):
        if thread.is_alive():
            continue
        if not thread.finished:
            # Implement retry logic here
            pass
        upload_threads.remove(thread)

    return 2


class UploadFileMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.file_size: int
        self.props: types.Props
        self.filepath: str
        self.log_state_name: str

        self._upload_progress_bytes = 0
        self.uploading = False

        correlation_id = str(uuid.uuid4())
        self.headers = utils.get_headers(correlation_id)

        self.finished = False

    def log(self, text: str, error: bool = False):
        self.props.render_state = text
        color = colors.RED if error else colors.GREEN
        ui.add_report(text, color=color)
        print(text)

    @property
    def upload_progress(self):
        return self._upload_progress_bytes / self.file_size

    def upload_file(self, upload_url: str, log_arg: str = 'render scene file'):
        self.uploading = True
        try:
            # TODO: Multipart upload
            upload_response = requests.put(
                upload_url,
                data=_read_in_chunks(self),
                stream=True,
            )
            assert upload_response.ok
            self.log(f'Uploaded {log_arg}')
        except Exception as e:
            self.log(f'Error when uploading {log_arg} ({e!r})', error=True)
            raise Exception(msg)
        finally:
            self.uploading = False


class _read_in_chunks:
    def __init__(
            self,
            render_thread: UploadFileMixin,
            blocksize: int = 2 ** 20):
        """Helper class that allows for streaming upload and update progress"""
        self.render_thread = render_thread
        self.blocksize = blocksize

    def __iter__(self):
        with open(self.render_thread.filepath, 'rb') as f:
            while True:
                data = f.read(self.blocksize)
                if not data:
                    break
                self.render_thread._upload_progress_bytes += len(data)
                msg = f'Uploading file: {self.render_thread.upload_progress:.1%}'
                setattr(self.render_thread.props, self.render_thread.log_state_name, msg)
                yield data

    def __len__(self):
        return self.render_thread.file_size


class RenderThread(UploadFileMixin, threading.Thread):
    def __init__(
            self,
            props: types.Props,
            engine: str,
            frame_start: int,
            frame_end: int):
        super().__init__(daemon=True)
        self.props = props
        self.engine = engine
        self.frame_start = frame_start
        self.frame_end = frame_end

        # Save job name on thread to avoid erros when changing asset name before job completes
        self.render_job_name = props.render_job_name
        self.log_state_name = 'render_state'

        self.tempdir = tempfile.mkdtemp()
        self.filepath = os.path.join(self.tempdir, 'export_render.blend')
        bpy.ops.wm.save_as_mainfile(filepath=self.filepath, compress=False, copy=True)
        self.file_size = os.path.getsize(self.filepath)

        self.job_progress = 0.0
        self.job_running = False

    def run(self):
        self.props.rendering = True
        try:
            render_scene_id, upload_url = self._create_render_view()
            self.upload_file(upload_url)
            self._confirm_file_upload(render_scene_id)
            job_id = self._create_job(render_scene_id)
            render_nrf_url = self._pool_job(job_id)
            if render_nrf_url:
                job_data = self._post_completed_job(render_scene_id, render_nrf_url)
                self._import_render(job_data)
        except Exception as e:
            self.log(f'Error in render job {self.render_job_name}:{e!r}')
            raise e
        else:
            self.finished = True
            self.log('Job finished successfully')
        finally:
            self.props.rendering = False
            time.sleep(5)
            self.props.render_state = ''

    def _create_render_view(self) -> Tuple[str, str]:
        url = paths.get_api_url('uploads')
        data = {
            'assetId': self.props.id,
            'originalFilename': os.path.basename(self.filepath),
            'id_parent': self.props.view_id,
            'metadata': {
                'render': {
                    'file_type': 'scene',
                    'job_name': self.render_job_name,
                }
            }
        }
        response = rerequests.post(url, json=data, headers=self.headers)
        assert response.ok, f'Error when creating render view on url={url}'

        dict_response = response.json()

        render_scene_id = dict_response['id']
        upload_url = dict_response['s3UploadUrl']
        return render_scene_id, upload_url

    def _confirm_file_upload(self, render_scene_id: str):
        url = paths.get_api_url('uploads_s3', render_scene_id, 'upload-file')
        rerequests.post(url, headers=self.headers)

    def _create_job(self, render_scene_id: str) -> str:
        self.log('Creating Job')
        job_url = paths.get_api_url('render_jobs')

        data = {
            'render_scene_id': render_scene_id,
            'engine': self.engine,
            'frame_start': self.frame_start,
            'frame_end': self.frame_end,
        }
        response = rerequests.post(job_url, json=data, headers=self.headers)
        assert response.ok, f'Error when creating job: {response.text}'

        job = response.json()
        return job['id']

    def _pool_job(self, job_id: str, pool_time: int = 5) -> str:
        self.job_running = True
        while self.job_running:
            url = paths.get_api_url('render_jobs', job_id)
            response = rerequests.get(url, headers=self.headers)
            job = response.json()

            if job['status'] == 'FINISHED':
                self.log('Job complete')
                self.job_running = False
            elif job['status'] == 'ERRORED':
                self.log('Error in job')
                self.job_running = False
                raise Exception(f'Error in render job: {job}')
            else:
                self.job_progress = job['progress']
                msg = f'Rendering {self.render_job_name}: {job["progress"]:.1%}'
                self.props.render_state = msg

                time.sleep(pool_time)
        return job.get('output_url', '')

    def _post_completed_job(self, render_scene_id: str, render_url: str) -> dict:
        url = paths.get_api_url('uploads')
        data = {
            'assetId': self.props.id,
            'originalFilename': render_url.rpartition('/')[2],
            'id_parent': render_scene_id,
            'url': render_url,
            'metadata': {
                'render': {
                    'file_type': 'output',
                    'job_name': self.render_job_name,
                    'environment': 'notrenderfarm',
                }
            }
        }
        response = rerequests.post(url, json=data, headers=self.headers)
        assert response.ok, response.text

        dict_response = response.json()
        return {
            'id': dict_response['id'],
            'file_url': dict_response['output_url'],
            'created': datetime.isoformat(datetime.utcnow()),
            'job_name': self.render_job_name,
        }

    def _import_render(self, job_data: dict):
        url = job_data['file_url']
        filename = paths.extract_filename_from_url(url)
        download_dir = paths.get_download_dirs(self.props.asset_type)[0]
        file_path = os.path.join(download_dir, filename)

        response = requests.get(url, stream=True)
        with open(file_path, 'wb') as f:
            f.write(response.content)

        job_data['file_path'] = file_path
        _, ext = os.path.splitext(filename)
        job_data['file_format'] = ext[1:] if len(ext) > 0 else ''

        img = bpy.data.images.load(file_path, check_existing=True)
        img.name = job_data['job_name']
        job_data['image'] = img

        # Append this way as property type is different depending on length
        if len(self.props.render_data['jobs']) == 0:
            self.props.render_data['jobs'] = [job_data]
        else:
            self.props.render_data['jobs'] += [job_data]


class RenderScene(Operator):
    """Render Scene online at notrenderfarm.com"""

    bl_idname = "hana3d.render_scene"
    bl_label = "Render Scene"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        props = utils.get_upload_props()
        return props is not None and not props.rendering

    def execute(self, context):
        props = utils.get_upload_props()

        if props.view_id == '':
            def draw_message(self, context):
                self.layout.label(text=message)
            title = "Can't render"
            message = "Please upload selected asset or select uploaded asset"
            bpy.context.window_manager.popup_menu(draw_message, title=title, icon='INFO')
            return {'FINISHED'}

        render_props = context.scene.Hana3DRender
        if render_props.frame_animation == 'FRAME':
            frame_start = context.scene.frame_current
            frame_end = context.scene.frame_current
        elif render_props.frame_animation == 'ANIMATION':
            frame_start = context.scene.frame_start
            frame_end = context.scene.frame_end

        thread = RenderThread(props, render_props.engine, frame_start, frame_end)
        thread.start()
        render_threads.append(thread)

        return {'FINISHED'}


class ImportRender(Operator):
    """Import finished render job"""

    bl_idname = "hana3d.import_render"
    bl_label = "Import render to scene"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        props = utils.get_upload_props()
        return len(props.render_data['jobs']) > 0

    def execute(self, context):
        props = utils.get_upload_props()
        for job in props.render_data['jobs']:
            if job['id'] != props.render_job_output:
                continue

            if job.get('image') is not None:
                # Image was already imported
                return {'FINISHED'}

            image = bpy.data.images.load(job['file_path'], check_existing=True)
            image.name = job['job_name']
            image['active'] = True
            job['image'] = image

            def draw(self, context):
                self.layout.label(text="Your render is now on your scene's Image Data list")
            context.window_manager.popup_menu(draw, title='Success')

            return {'FINISHED'}
        print(f'Cound not find render job id={job["id"]}')
        return {'CANCELLED'}


class RemoveRender(Operator):
    """Remove finished render job"""

    bl_idname = "hana3d.remove_render"
    bl_label = "Remove render"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        props = utils.get_upload_props()
        return props.render_job_output != ''

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

    def execute(self, context):
        props = utils.get_upload_props()
        id_job = props.render_job_output
        job, = [j for j in props.render_data['jobs'] if j['id'] == id_job]

        if job.get('image') is not None:  # Case when image was not imported to scene
            bpy.data.images.remove(job['image'])

        self.remove_from_hana3d_backend(id_job)

        name = job['job_name']  # Get name before job is de-referenced
        self.remove_from_props(id_job, props)
        self.switch_active_render_job(props)

        ui.add_report(f'Deleted render {name}')
        return {'FINISHED'}

    @staticmethod
    def remove_from_hana3d_backend(id_job: str):
        url = paths.get_api_url('renders', id_job)
        response = rerequests.delete(url, headers=utils.get_headers())
        assert response.ok, f'Error deleting render using DELETE on {url}: {response.text}'

    @staticmethod
    def remove_from_props(id_job: str, props: types.Props):
        jobs = [
            job
            for job in props.render_data['jobs']
            if job['id'] != id_job
        ]
        props.render_data['jobs'] = jobs

    @staticmethod
    def switch_active_render_job(props: types.Props):
        if len(props.render_data['jobs']) == 0:
            return
        id_first_job = props.render_data['jobs'][0]['id']
        props.render_job_output = id_first_job


class OpenImage(Operator):
    """Open image from computer"""

    bl_idname = "hana3d.open_image"
    bl_label = "Open image"
    bl_options = {'REGISTER', 'UNDO'}

    file_path: StringProperty(name='File', subtype='FILE_PATH')
    files: CollectionProperty(
        type=bpy.types.OperatorFileListElement,
        options={'HIDDEN', 'SKIP_SAVE'}
    )
    directory: StringProperty(
        maxlen=1024,
        subtype='FILE_PATH',
        options={'HIDDEN', 'SKIP_SAVE'}
    )

    filter_image: BoolProperty(default=True, options={'HIDDEN', 'SKIP_SAVE'})
    filter_movie: BoolProperty(default=False, options={'HIDDEN', 'SKIP_SAVE'})
    filter_folder: BoolProperty(default=True, options={'HIDDEN', 'SKIP_SAVE'})

    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        for file in self.files:
            image = load_image(
                file.name,
                self.directory,
                check_existing=True,
                force_reload=False
            )
            image['active'] = True
        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


class UploadThread(UploadFileMixin, threading.Thread):
    def __init__(self, context, props: types.Props):
        super().__init__(daemon=True)
        self.props = props
        self.context = context
        self.log_state_name = 'upload_render_state'

    def run(self):
        self.props.uploading_render = True
        try:
            img_name = self.props.active_image
            img = self.context.blend_data.images[img_name]

            self.set_image_filepath(img)
            job = {
                'file_path': self.filepath,
                'created': datetime.isoformat(datetime.utcnow()),
                'job_name': self.props.render_job_name,
                'file_url': None,
                'image': img,
                'file_format': self.file_extension,
            }

            self.upload_render(job)
            self.append_job_to_props(job)
        except Exception as e:
            self.log(f'Error when uploading render {self.props.render_job_name}:{e!r}')
            raise e
        else:
            self.finished = True
            self.log('Uploaded render image')
        finally:
            self.props.uploading_render = False
            time.sleep(5)
            self.props.upload_render_state = ''

        return {'FINISHED'}

    def set_image_filepath(self, img):
        if img.filepath == '':
            download_dir = paths.get_download_dirs(self.props.asset_type)[0]
            extension = self.context.scene.render.file_extension
            self.filepath = os.path.join(download_dir, str(uuid.uuid4()) + extension)
            img.save_render(self.filepath, scene=self.context.scene)
        else:
            self.filepath = img.filepath
            _, extension = os.path.splitext(img.filepath)
        self.file_size = os.path.getsize(self.filepath)
        self.file_extension = extension

    def upload_render(self, job: dict) -> str:
        render_output_id, upload_url = self._create_render_output_view(job)
        self.upload_file(upload_url, log_arg='render image')
        self._confirm_file_upload(render_output_id)

        job['id'] = render_output_id

    def _create_render_output_view(self, job: dict) -> Tuple[str, str]:
        url = paths.get_api_url('uploads')
        data = {
            'assetId': self.props.id,
            'originalFilename': os.path.basename(job['file_path']),
            'id_parent': self.props.view_id,
            'metadata': {
                'render': {
                    'file_type': 'output',
                    'job_name': job['job_name'],
                    'environment': 'local',
                }
            }
        }
        response = rerequests.post(url, json=data, headers=self.headers)
        assert response.ok, f'Error when creating render output view on url={url}:\n{response.text}'

        dict_response = response.json()

        render_scene_id = dict_response['id']
        upload_url = dict_response['s3UploadUrl']
        return render_scene_id, upload_url

    def _confirm_file_upload(self, render_scene_id: str):
        url = paths.get_api_url('uploads_s3', render_scene_id, 'upload-file')
        rerequests.post(url, headers=self.headers)

    def append_job_to_props(self, job: dict):
        if 'jobs' not in self.props.render_data or len(self.props.render_data['jobs']) == 0:
            self.props.render_data['jobs'] = [job]
        else:
            self.props.render_data['jobs'] += [job]


class UploadImage(Operator):
    """Upload existing render image"""

    bl_idname = "hana3d.upload_render_image"
    bl_label = "Upload to Hana3D"
    bl_options = {'REGISTER', 'UNDO'}
    bl_icon = 'EXPORT'

    @classmethod
    def poll(cls, context):
        props = utils.get_upload_props()
        return props is not None and props.active_image != '' and not props.uploading_render

    def execute(self, context):
        props = utils.get_upload_props()
        self.props = props

        thread = UploadThread(context, props)
        thread.start()
        upload_threads.append(thread)

        return {'FINISHED'}


classes = (
    RenderScene,
    ImportRender,
    RemoveRender,
    OpenImage,
    UploadImage,
)

# Dictionary to store asset previews. Keys are the view_id's
render_previews = defaultdict(bpy.utils.previews.new)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.app.timers.register(threads_timer)


def unregister():
    if bpy.app.timers.is_registered(threads_timer):
        bpy.app.timers.unregister(threads_timer)

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

    for pcoll in render_previews.values():
        bpy.utils.previews.remove(pcoll)
    render_previews.clear()
