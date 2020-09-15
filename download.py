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

    append_link = reload(append_link)
    colors = reload(colors)
    paths = reload(paths)
    rerequests = reload(rerequests)
    ui = reload(ui)
    utils = reload(utils)
else:
    from hana3d import append_link, colors, paths, rerequests, ui, utils

import copy
import os
import shutil
import sys
import threading
from typing import List

import bpy
import requests
from bpy.app.handlers import persistent
from bpy.props import (
    BoolProperty,
    EnumProperty,
    FloatProperty,
    FloatVectorProperty,
    IntProperty,
    StringProperty
)

download_threads = {}
append_threads = {}


def check_missing():
    '''checks for missing files, and possibly starts re-download of these into the scene'''
    # missing libs:
    # TODO: put these into a panel and let the user decide if these should be downloaded.
    missing = []
    for library in bpy.data.libraries:
        fp = library.filepath
        if fp.startswith('//'):
            fp = bpy.path.abspath(fp)
        if not os.path.exists(fp) and library.get('asset_data') is not None:
            missing.append(library)

    # print('missing libraries', missing)

    for library in missing:
        asset_data = library['asset_data']
        downloaded = check_existing(asset_data)
        if downloaded:
            try:
                library.reload()
            except Exception:
                download(library['asset_data'], redownload=True)
        else:
            download(library['asset_data'], redownload=True)


def check_unused():
    '''find assets that have been deleted from scene but their library is still present.'''

    used_libs = []
    for ob in bpy.data.objects:
        if ob.instance_collection is not None and ob.instance_collection.library is not None:
            # used_libs[ob.instance_collection.name] = True
            if ob.instance_collection.library not in used_libs:
                used_libs.append(ob.instance_collection.library)

        for ps in ob.particle_systems:
            if (
                ps.settings.render_type == 'GROUP'
                and ps.settings.instance_collection is not None
                and ps.settings.instance_collection.library not in used_libs
            ):
                used_libs.append(ps.settings.instance_collection)

    for library in bpy.data.libraries:
        if library not in used_libs:
            print('attempt to remove this library: ', library.filepath)
            # have to unlink all groups, since the file is a 'user'
            # even if the groups aren't used at all...
            for user_id in library.users_id:
                if type(user_id) == bpy.types.Collection:
                    bpy.data.collections.remove(user_id)
            library.user_clear()


@persistent
def scene_save(context):
    ''' does cleanup of hana3d props and sends a message to the server about assets used.'''
    # TODO this can be optimized by merging these 2 functions, since both iterate over all objects.
    if not bpy.app.background:
        check_unused()


@persistent
def scene_load(context):
    '''restart broken downloads on scene load'''
    global download_threads
    download_threads = {}

    check_missing()


def download_file(file_path: str, url: str) -> str:
    response = requests.get(url, stream=True)

    # Write to temp file and then rename to avoid reading errors as file is being downloaded
    tmp_file = file_path + '_tmp'
    with open(tmp_file, 'wb') as f:
        f.write(response.content)
    os.rename(tmp_file, file_path)


def download_renders(jobs: List[dict]):
    """Download render files from urls and write local paths to jobs dictionaries"""
    for job in jobs:
        if not os.path.exists(job['file_path']):
            thread = threading.Thread(
                target=download_file,
                args=(job['file_path'], job['file_url']),
                daemon=True,
            )
            thread.start()


def add_file_paths(jobs: List[dict], download_dir: str):
    for job in jobs:
        url = job['file_url']
        filename = paths.extract_filename_from_url(url)

        file_path = os.path.join(download_dir, filename)
        job['file_path'] = file_path


def get_render_jobs(view_id: str) -> List[dict]:
    url = paths.get_api_url('renders', query={'view_id': view_id})
    response = rerequests.get(url, headers=utils.get_headers())
    assert response.ok, response.text

    return response.json()


def set_thumbnail(asset_data, asset):
    thumbnail_name = asset_data['thumbnail'].split(os.sep)[-1]
    tempdir = paths.get_temp_dir(f'{asset_data["asset_type"]}_search')
    thumbpath = os.path.join(tempdir, thumbnail_name)
    asset_thumbs_dir = paths.get_download_dirs(asset_data["asset_type"])[0]
    asset_thumb_path = os.path.join(asset_thumbs_dir, thumbnail_name)
    shutil.copy(thumbpath, asset_thumb_path)
    asset.hana3d.thumbnail = asset_thumb_path


def update_downloaded_progress(view_id: str, progress: int):
    sr = bpy.context.scene.get('search results')
    if sr is None:
        utils.p('search results not found')
        return
    for r in sr:
        if r.get('view_id') == view_id:
            r['downloaded'] = progress
            return


# @bpy.app.handlers.persistent
def timer_update():  # TODO might get moved to handle all hana3d stuff, not to slow down.
    '''check for running and finished downloads and react. write progressbars too.'''
    if len(download_threads) == 0:
        return 1.0
    for view_id, thread in download_threads.items():
        asset_data = thread.asset_data
        tcom = thread.tcom

        if thread.is_alive():
            update_downloaded_progress(view_id, tcom.progress)
            continue

        if tcom.error:
            sprops = utils.get_search_props()
            sprops.report = tcom.report
            download_threads.pop(view_id)
            ui.add_report(f'Error when downloading {asset_data["name"]}')
            continue

        if bpy.context.mode == 'EDIT' and asset_data['asset_type'] in ('model', 'material'):
            continue

        utils.p('appending asset')
        download_threads.pop(view_id)

        file_names = paths.get_download_filenames(asset_data)
        # duplicate file if the global and subdir are used in prefs
        # todo this should try to check if both files exist and are ok.
        if len(file_names) == 2:
            shutil.copyfile(file_names[0], file_names[1])

        if tcom.passargs.get('redownload'):
            # handle lost libraries here:
            for library in bpy.data.libraries:
                if (
                    library.get('asset_data') is not None
                    and library['asset_data']['view_id'] == asset_data['view_id']
                ):
                    library.filepath = file_names[-1]
                    library.reload()
        else:
            try:
                append_asset(asset_data, **tcom.passargs)
                update_downloaded_progress(asset_data['view_id'], 100)
            except Exception as e:
                ui.add_report(f'Error when appendig {asset_data["name"]} to scene: {e}')
        utils.p('finished download thread')
    return 0.5


class ThreadCom:  # object passed to threads to read background process stdout info
    def __init__(self):
        self.file_size = 1000000000000000  # property that gets written to.
        self.downloaded = 0
        self.lasttext = ''
        self.error = False
        self.report = ''
        self.progress = 0.0
        self.passargs = {}


class Downloader(threading.Thread):
    def __init__(self, asset_data: dict, tcom: ThreadCom):
        super(Downloader, self).__init__()
        self.asset_data = asset_data
        self.tcom = tcom
        self._stop_event = threading.Event()

    def stop(self):
        self._stop_event.set()

    def stopped(self):
        return self._stop_event.is_set()

    # def main_download_thread(asset_data, tcom):
    def run(self):
        '''try to download file from hana3d'''
        asset_data = self.asset_data
        tcom = self.tcom

        if tcom.error:
            return
        # only now we can check if the file already exists.
        # This should have 2 levels, for materials
        # different than for the non free content.
        # delete is here when called after failed append tries.
        if check_existing(asset_data) and not tcom.passargs.get('delete'):
            # this sends the thread for processing,
            # where another check should occur,
            # since the file might be corrupted.
            tcom.downloaded = 100
            utils.p('not downloading, trying to append again')
            return

        file_name = paths.get_download_filenames(asset_data)[0]  # prefer global dir if possible.
        # for k in asset_data:
        #    print(asset_data[k])
        if self.stopped():
            utils.p('stopping download: ' + asset_data['name'])
            return

        with open(file_name, "wb") as f:
            print("Downloading %s" % file_name)

            response = requests.get(asset_data['download_url'], stream=True)
            total_length = response.headers.get('Content-Length')

            if total_length is None:  # no content length header
                f.write(response.content)
            else:
                tcom.file_size = int(total_length)
                dl = 0
                for data in response.iter_content(chunk_size=4096):
                    dl += len(data)
                    tcom.downloaded = dl
                    tcom.progress = int(100 * tcom.downloaded / tcom.file_size)
                    f.write(data)
                    if self.stopped():
                        utils.p('stopping download: ' + asset_data['name'])
                        f.close()
                        os.remove(file_name)
                        return


def download(asset_data, **kwargs):
    '''start the download thread'''

    tcom = ThreadCom()
    tcom.passargs = kwargs

    # incoming data can be either directly dict from python, or blender id property
    # (recovering failed downloads on reload)
    if type(asset_data) == dict:
        asset_data = copy.deepcopy(asset_data)
    else:
        asset_data = asset_data.to_dict()
    thread = Downloader(asset_data, tcom)
    thread.start()

    view_id = asset_data['view_id']
    download_threads[view_id] = thread


def add_import_params(thread: Downloader, location, rotation):
    params = {
        'location': location,
        'rotation': rotation,
    }
    thread.tcom.passargs['import_params'].append(params)


def check_existing(asset_data):
    ''' check if the object exists on the hard drive'''
    file_names = paths.get_download_filenames(asset_data)

    utils.p('check if file already exists')
    if len(file_names) == 2:
        # TODO this should check also for failed or running downloads.
        # If download is running, assign just the running thread.
        # if download isn't running but the file is wrong size,
        #  delete file and restart download (or continue downoad? if possible.)
        if os.path.isfile(file_names[0]) and not os.path.isfile(file_names[1]):
            shutil.copy(file_names[0], file_names[1])
        # only in case of changed settings or deleted/moved global dict.
        elif not os.path.isfile(file_names[0]) and os.path.isfile(file_names[1]):
            shutil.copy(file_names[1], file_names[0])

    if len(file_names) == 0 or not os.path.isfile(file_names[0]):
        return False

    newer_asset_in_server = (
        asset_data.get('created') is not None
        and float(asset_data['created']) > float(os.path.getctime(file_names[0]))
    )
    if newer_asset_in_server:
        os.remove(file_names[0])
        return False

    return True


def append_asset(asset_data, **kwargs):
    asset_name = asset_data['name']
    utils.p(f'appending asset {asset_name}')

    file_names = paths.get_download_filenames(asset_data)
    if len(file_names) == 0 or not os.path.isfile(file_names[-1]):
        raise FileNotFoundError(f'Could not find file for asset {asset_name}')

    kwargs['name'] = asset_data['name']

    file_names = paths.get_download_filenames(asset_data)
    scene = bpy.context.scene

    if asset_data['asset_type'] == 'scene':
        scene = append_link.append_scene(file_names[0], link=False, fake_user=False)
        parent = scene

    if asset_data['asset_type'] == 'model':
        sprops = scene.hana3d_models
        if sprops.append_method == 'LINK_COLLECTION':
            sprops.append_link = 'LINK'
            sprops.import_as = 'GROUP'
        else:
            sprops.append_link = 'APPEND'
            sprops.import_as = 'INDIVIDUAL'

        append_or_link = sprops.append_link
        asset_in_scene = check_asset_in_scene(asset_data)
        link = (asset_in_scene == 'LINK') or (append_or_link == 'LINK')

        import_params = kwargs.get('import_params')
        if import_params:
            for param in import_params:
                if link is True:
                    parent, newobs = append_link.link_collection(
                        file_names[-1],
                        location=param['location'],
                        rotation=param['rotation'],
                        link=link,
                        name=asset_data['name'],
                        parent=kwargs.get('parent'),
                    )
                else:
                    parent, newobs = append_link.append_objects(
                        file_names[-1],
                        location=param['location'],
                        rotation=param['rotation'],
                        link=link,
                        name=asset_data['name'],
                        parent=kwargs.get('parent'),
                    )

                if parent.type == 'EMPTY' and link:
                    bmin = asset_data['bbox_min']
                    bmax = asset_data['bbox_max']
                    size_min = min(
                        1.0,
                        (bmax[0] - bmin[0] + bmax[1] - bmin[1] + bmax[2] - bmin[2]) / 3
                    )
                    parent.empty_display_size = size_min

        elif kwargs.get('model_location') is not None:
            if link is True:
                parent, newobs = append_link.link_collection(
                    file_names[-1],
                    location=kwargs['model_location'],
                    rotation=kwargs['model_rotation'],
                    link=link,
                    name=asset_data['name'],
                    parent=kwargs.get('parent'),
                )
            else:
                parent, newobs = append_link.append_objects(
                    file_names[-1],
                    location=kwargs['model_location'],
                    rotation=kwargs['model_rotation'],
                    link=link,
                    parent=kwargs.get('parent'),
                )
            if parent.type == 'EMPTY' and link:
                bmin = asset_data['bbox_min']
                bmax = asset_data['bbox_max']
                size_min = min(1.0, (bmax[0] - bmin[0] + bmax[1] - bmin[1] + bmax[2] - bmin[2]) / 3)
                parent.empty_display_size = size_min

        if link:
            group = parent.instance_collection

            lib = group.library
            lib['asset_data'] = asset_data

    elif asset_data['asset_type'] == 'material':
        inscene = False
        for m in bpy.data.materials:
            if m.hana3d.view_id == asset_data['view_id']:
                inscene = True
                material = m
                break
        if not inscene:
            material = append_link.append_material(file_names[-1], link=False, fake_user=False)
        target_object = bpy.data.objects[kwargs['target_object']]

        if len(target_object.material_slots) == 0:
            target_object.data.materials.append(material)
        else:
            target_object.material_slots[kwargs['material_target_slot']].material = material

        parent = material

    scene['assets used'] = scene.get('assets used', {})
    scene['assets used'][asset_data['view_id']] = asset_data.copy()

    parent.hana3d.clear_data()
    parent['asset_data'] = asset_data

    if asset_data['asset_type'] == 'model':  # TODO: read object metadata from server
        utils.fill_object_metadata(parent)

    set_thumbnail(asset_data, parent)

    parent.hana3d.id = asset_data['id']
    parent.hana3d.view_id = asset_data['view_id']
    parent.hana3d.name = asset_data['name']
    parent.hana3d.tags = ','.join(asset_data['tags'])
    parent.hana3d.description = asset_data['description']

    jobs = get_render_jobs(asset_data['view_id'])
    download_dir = paths.get_download_dirs(asset_data['asset_type'])[0]
    add_file_paths(jobs, download_dir)
    parent.hana3d.render_data['jobs'] = jobs
    download_renders(jobs)

    if 'libraries' in asset_data:
        hana3d_class = type(parent.hana3d)
        for library in asset_data['libraries']:
            for i in range(parent.hana3d.libraries_count):
                library_entry = getattr(hana3d_class, f'library_{i}')
                name = library_entry[1]['name']
                library_info = parent.hana3d.libraries_info[name]

                if library_info['id'] == library['library_id']:
                    library_prop = getattr(parent.hana3d, f'library_{i}')
                    library_prop = True  # noqa:F841
                    break

                if 'metadata' in library and library['metadata'] is not None:
                    for view_prop in library['metadata']['view_props']:
                        name = f'{library["name"]} {library_info["metadata"]["view_props"][key]}'
                        parent.hana3d.custom_props_info[name] = {
                            'key': view_prop['key'],
                            'library_name': library["name"],
                            'library_id': library['id_library']
                        }
                        parent.hana3d.custom_props[name] = view_prop['value']

    if asset_data['asset_type'] == 'scene':
        if bpy.context.scene.hana3d_scene.merge_add == 'ADD':
            for window in bpy.context.window_manager.windows:
                window.scene = bpy.data.scenes[asset_data['name']]

    bpy.ops.wm.undo_push_context(message='add %s to scene' % asset_data['name'])


def check_asset_in_scene(asset_data):
    '''checks if the asset is already in scene. If yes,
    modifies asset data so the asset can be reached again.'''
    scene = bpy.context.scene
    au = scene.get('assets used', {})

    id = asset_data.get('view_id')
    if id in au.keys():
        ad = au[id]
        if ad.get('file_name') is not None:

            asset_data['file_name'] = ad['file_name']
            asset_data['download_url'] = ad['download_url']

            c = bpy.data.collections.get(ad['name'])
            if c is not None:
                if c.users > 0:
                    return 'LINK'
            return 'APPEND'
    return ''


def start_download(asset_data, **kwargs):
    '''
    check if file isn't downloading or doesn't exist, then start new download
    '''
    if asset_data['view_id'] in download_threads:
        if asset_data['asset_type'] in ('model', 'material'):
            thread = download_threads[asset_data['view_id']]
            add_import_params(thread, kwargs['model_location'], kwargs['model_rotation'])
        return

    fexists = check_existing(asset_data)
    asset_in_scene = check_asset_in_scene(asset_data)

    if fexists and asset_in_scene:
        append_asset(asset_data, **kwargs)
        return

    if asset_data['asset_type'] in ('model', 'material'):
        params = {
            'location': kwargs['model_location'],
            'rotation': kwargs['model_rotation'],
        }
        download(asset_data, import_params=[params], **kwargs)

    elif asset_data['asset_type'] == 'scene':
        download(asset_data, **kwargs)


asset_types = (
    ('MODEL', 'Model', 'set of objects'),
    ('SCENE', 'Scene', 'scene'),
    ('MATERIAL', 'Material', 'any .blend Material'),
    ('ADDON', 'Addon', 'addnon'),
)


class Hana3DKillDownloadOperator(bpy.types.Operator):
    """Kill a download"""

    bl_idname = "scene.hana3d_download_kill"
    bl_label = "Hana3D Kill Asset Download"
    bl_options = {'REGISTER', 'INTERNAL'}

    view_id: StringProperty()

    def execute(self, context):
        thread = download_threads.pop(self.view_id)
        thread.stop()
        return {'FINISHED'}


class Hana3DDownloadOperator(bpy.types.Operator):
    """Download and link asset to scene. Only link if asset already available locally."""

    bl_idname = "scene.hana3d_download"
    bl_label = "Hana3D Asset Download"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    asset_type: EnumProperty(
        name="Type",
        items=asset_types,
        description="Type of download",
        default="MODEL",
    )
    asset_index: IntProperty(
        name="Asset Index",
        description='asset index in search results',
        default=-1
    )

    target_object: StringProperty(
        name="Target Object",
        description="Material or object target for replacement",
        default=""
    )

    material_target_slot: IntProperty(
        name="Asset Index",
        description='asset index in search results',
        default=0
    )
    model_location: FloatVectorProperty(name='Asset Location', default=(0, 0, 0))
    model_rotation: FloatVectorProperty(name='Asset Rotation', default=(0, 0, 0))

    replace: BoolProperty(
        name='Replace',
        description='replace selection with the asset',
        default=False
    )

    cast_parent: StringProperty(name="Particles Target Object", description="", default="")

    def execute(self, context):
        s = bpy.context.scene
        sr = s['search results']

        # TODO CHECK ALL OCCURRENCES OF PASSING BLENDER ID PROPS TO THREADS!
        asset_data = sr[self.asset_index].to_dict()
        au = s.get('assets used')
        if au is None:
            s['assets used'] = {}

        atype = asset_data['asset_type']
        if (
            bpy.context.mode != 'OBJECT'
            and (atype == 'model' or atype == 'material')
            and bpy.context.view_layer.objects.active is not None
        ):
            bpy.ops.object.mode_set(mode='OBJECT')

        if self.replace:  # cleanup first, assign later.
            obs = utils.get_selected_models()

            for ob in obs:
                kwargs = {
                    'cast_parent': self.cast_parent,
                    'target_object': ob.name,
                    'material_target_slot': ob.active_material_index,
                    'model_location': tuple(ob.matrix_world.translation),
                    'model_rotation': tuple(ob.matrix_world.to_euler()),
                    'replace': False,
                    'parent': ob.parent,
                }
                utils.delete_hierarchy(ob)
                start_download(asset_data, **kwargs)
        else:
            kwargs = {
                'cast_parent': self.cast_parent,
                'target_object': self.target_object,
                'material_target_slot': self.material_target_slot,
                'model_location': tuple(self.model_location),
                'model_rotation': tuple(self.model_rotation),
                'replace': False,
            }

            start_download(asset_data, **kwargs)
        return {'FINISHED'}


class Hana3DBatchDownloadOperator(bpy.types.Operator):
    """Download and link all preview assets to scene."""

    bl_idname = "scene.hana3d_batch_download"
    bl_label = "Hana3D Batch Download"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    object_count: IntProperty(
        name="Object Count",
        description='number of objects imported to scene',
        default=0,
        options={'HIDDEN'}
    )

    grid_distance: FloatProperty(
        name="Grid Distance",
        description='distance between objects on the grid',
        default=3
    )

    def _get_location(self):
        x = y = 0
        dx = 0
        dy = -1
        for i in range(self.object_count):
            if x == y or (x < 0 and x == -y) or (x > 0 and x == 1 - y):
                dx, dy = -dy, dx
            x, y = x + dx, y + dy
        self.object_count += 1
        return (self.grid_distance * x, self.grid_distance * y, 0)

    def execute(self, context):
        self.object_count = 0
        scene = context.scene
        if 'search results' not in scene:
            return {'CANCELLED'}
        sr = scene['search results']

        print('len: ', len(sr))

        for result in sr:
            asset_data = result.to_dict()
            location = self._get_location()
            kwargs = {
                'cast_parent': "",
                'target_object': "",
                'material_target_slot': 0,
                'model_location': tuple(location),
                'model_rotation': tuple((0, 0, 0)),
                'replace': False,
            }

            start_download(asset_data, **kwargs)
        return {'FINISHED'}


classes = (
    Hana3DDownloadOperator,
    Hana3DBatchDownloadOperator,
    Hana3DKillDownloadOperator
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.app.handlers.load_post.append(scene_load)
    bpy.app.handlers.save_pre.append(scene_save)

    bpy.app.timers.register(timer_update)


def unregister():
    if bpy.app.timers.is_registered(timer_update):
        bpy.app.timers.unregister(timer_update)

    bpy.app.handlers.save_pre.remove(scene_save)
    bpy.app.handlers.load_post.remove(scene_load)

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
