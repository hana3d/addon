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
    bg_blender = reload(bg_blender)
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
    FloatVectorProperty,
    IntProperty,
    StringProperty
)
download_threads = []


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
    download_threads = []

    # commenting this out - old restore broken download on scene start.
    # Might come back if downloads get recorded in scene
    # reset_asset_ids = {}
    # reset_obs = {}
    # for ob in bpy.context.scene.collection.objects:
    #     if ob.name[:12] == 'downloading ':
    #         obn = ob.name
    #
    #         asset_data = ob['asset_data']
    #
    #         # obn.replace('#', '')
    #         # if asset_data['id'] not in reset_asset_ids:
    #
    #         if reset_obs.get(asset_data['id']) is None:
    #             reset_obs[asset_data['id']] = [obn]
    #             reset_asset_ids[asset_data['id']] = asset_data
    #         else:
    #             reset_obs[asset_data['id']].append(obn)
    # for asset_id in reset_asset_ids:
    #     asset_data = reset_asset_ids[asset_id]
    #     done = False
    #     if check_existing(asset_data):
    #         for obname in reset_obs[asset_id]:
    #             downloader = s.collection.objects[obname]
    #             done = try_finished_append(asset_data,
    #                                        model_location=downloader.location,
    #                                        model_rotation=downloader.rotation_euler)
    #
    #     if not done:
    #         downloading = check_downloading(asset_data)
    #         if not downloading:
    #             print('redownloading %s' % asset_data['name'])
    #             download(asset_data, downloaders=reset_obs[asset_id], delete=True)

    # check for group users that have been deleted, remove the groups /files from the file...
    # TODO scenes fixing part... download the assets not present on drive,
    # and erase from scene linked files that aren't used in the scene.
    # print('continue downlaods ', time.time() - t)
    check_missing()
    # print('missing check', time.time() - t)


def download_single_file(file_path: str, url: str) -> str:
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
                target=download_single_file,
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


def append_asset(asset_data, **kwargs):  # downloaders=[], location=None,
    '''Link asset to the scene'''

    file_names = paths.get_download_filenames(asset_data)
    scene = bpy.context.scene

    user_preferences = bpy.context.preferences.addons['hana3d'].preferences

    if user_preferences.api_key == '':
        user_preferences.asset_counter += 1

    if asset_data['asset_type'] == 'scene':
        scene = append_link.append_scene(file_names[0], link=False, fake_user=False)
        parent = scene

    if asset_data['asset_type'] == 'model':
        s = bpy.context.scene
        downloaders = kwargs.get('downloaders')
        s = bpy.context.scene
        sprops = s.hana3d_models
        if sprops.append_method == 'LINK_COLLECTION':
            sprops.append_link = 'LINK'
            sprops.import_as = 'GROUP'
        else:
            sprops.append_link = 'APPEND'
            sprops.import_as = 'INDIVIDUAL'

        append_or_link = sprops.append_link
        asset_in_scene = check_asset_in_scene(asset_data)
        link = (asset_in_scene == 'LINK') or (append_or_link == 'LINK')

        if downloaders:
            for downloader in downloaders:
                if link is True:
                    parent, newobs = append_link.link_collection(
                        file_names[-1],
                        location=downloader['location'],
                        rotation=downloader['rotation'],
                        link=link,
                        name=asset_data['name'],
                        parent=kwargs.get('parent'),
                    )
                else:
                    parent, newobs = append_link.append_objects(
                        file_names[-1],
                        location=downloader['location'],
                        rotation=downloader['rotation'],
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

    parent['asset_data'] = asset_data

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

    if hasattr(parent.hana3d, 'custom_props') and 'metadata' in asset_data:
        if 'product_info' in asset_data['metadata']:
            product_info = asset_data['metadata'].pop('product_info')
            clients = []
            skus = []
            for client_sku in product_info:
                clients.append(client_sku['client'])
                skus.append(client_sku['sku'])
            if hasattr(parent.hana3d, 'client') and hasattr(parent.hana3d, 'sku'):
                parent.hana3d.client = ','.join(clients)
                parent.hana3d.sku = ','.join(skus)
            else:
                parent.hana3d.custom_props['client'] = ','.join(clients)
                parent.hana3d.custom_props['sku'] = ','.join(skus)

        for key, value in asset_data['metadata'].items():
            parent.hana3d.custom_props[key] = value

    bpy.ops.wm.undo_push_context(message='add %s to scene' % asset_data['name'])


def set_thumbnail(asset_data, asset):
    thumbnail_name = asset_data['thumbnail'].split(os.sep)[-1]
    tempdir = paths.get_temp_dir(f'{asset_data["asset_type"]}_search')
    thumbpath = os.path.join(tempdir, thumbnail_name)
    asset_thumbs_dir = paths.get_download_dirs(asset_data["asset_type"])[0]
    asset_thumb_path = os.path.join(asset_thumbs_dir, thumbnail_name)
    shutil.copy(thumbpath, asset_thumb_path)
    asset.hana3d.thumbnail = asset_thumb_path


# @bpy.app.handlers.persistent
def timer_update():  # TODO might get moved to handle all hana3d stuff, not to slow down.
    '''check for running and finished downloads and react. write progressbars too.'''
    global download_threads
    if len(download_threads) == 0:
        return 1.0
    for threaddata in download_threads:
        t = threaddata[0]
        asset_data = threaddata[1]
        tcom = threaddata[2]

        if t.is_alive():  # set downloader size
            sr = bpy.context.scene.get('search results')
            if sr is not None:
                for r in sr:
                    if asset_data['view_id'] == r.get('view_id'):
                        r['downloaded'] = tcom.progress

        if not t.is_alive():
            if tcom.error:
                sprops = utils.get_search_props()
                sprops.report = tcom.report
                download_threads.remove(threaddata)
                return
            file_names = paths.get_download_filenames(asset_data)

            at = asset_data['asset_type']
            # don't do this stuff in editmode and other modes, just wait...
            if (
                (
                    bpy.context.mode == 'OBJECT'
                    and (at == 'model' or at == 'material')
                )
                or at == 'scene'
            ):
                download_threads.remove(threaddata)

                # duplicate file if the global and subdir are used in prefs
                # todo this should try to check if both files exist and are ok.
                if len(file_names) == 2:
                    shutil.copyfile(file_names[0], file_names[1])

                utils.p('appending asset')
                # progress bars:

                # we need to check if mouse isn't down, which means an operator can be running.

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
                    done = try_finished_append(asset_data, **tcom.passargs)
                    if not done:
                        tcom.passargs['retry_counter'] = tcom.passargs.get('retry_counter', 0) + 1
                        download(asset_data, **tcom.passargs)
                    if bpy.context.scene['search results'] is not None and done:
                        for sres in bpy.context.scene['search results']:
                            if asset_data['view_id'] == sres['view_id']:
                                sres['downloaded'] = 100

                utils.p('finished download thread')
    return 0.5


def download_file(asset_data):
    # this is a simple non-threaded way to download files for background resolution genenration tool
    file_name = paths.get_download_filenames(asset_data)[0]  # prefer global dir if possible.

    if check_existing(asset_data):
        # this sends the thread for processing,
        # where another check should occur,
        # since the file might be corrupted.
        utils.p('not downloading, already in db')
        return file_name

    with open(file_name, "wb") as f:
        print("Downloading %s" % file_name)

        response = requests.get(asset_data['download_url'], stream=True)
        total_length = response.headers.get('Content-Length')

        if total_length is None:  # no content length header
            f.write(response.content)
        else:
            dl = 0
            for data in response.iter_content(chunk_size=4096):
                dl += len(data)
                print(dl)
                f.write(data)
    return file_name


class Downloader(threading.Thread):
    def __init__(self, asset_data, tcom):
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


class ThreadCom:  # object passed to threads to read background process stdout info
    def __init__(self):
        self.file_size = 1000000000000000  # property that gets written to.
        self.downloaded = 0
        self.lasttext = ''
        self.error = False
        self.report = ''
        self.progress = 0.0
        self.passargs = {}


def download(asset_data, **kwargs):
    '''start the download thread'''

    tcom = ThreadCom()
    tcom.passargs = kwargs

    if kwargs.get('retry_counter', 0) > 3:
        sprops = utils.get_search_props()
        report = f"Maximum retries exceeded for {asset_data['name']}"
        sprops.report = report
        ui.add_report(report, 5, colors.RED)

        utils.p(sprops.report)
        return

    # incoming data can be either directly dict from python, or blender id property
    # (recovering failed downloads on reload)
    if type(asset_data) == dict:
        asset_data = copy.deepcopy(asset_data)
    else:
        asset_data = asset_data.to_dict()
    readthread = Downloader(asset_data, tcom)
    readthread.start()

    global download_threads
    download_threads.append([readthread, asset_data, tcom])


def check_downloading(asset_data, **kwargs):
    ''' check if an asset is already downloading, if yes,
    just make a progress bar with downloader object.'''
    global download_threads

    downloading = False

    for p in download_threads:
        p_asset_data = p[1]
        if p_asset_data['view_id'] == asset_data['view_id']:
            at = asset_data['asset_type']
            if at in ('model', 'material'):
                downloader = {
                    'location': kwargs['model_location'],
                    'rotation': kwargs['model_rotation'],
                }
                p[2].passargs['downloaders'].append(downloader)
            downloading = True

    return downloading


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


def try_finished_append(asset_data, **kwargs):  # location=None, material_target=None):
    ''' try to append asset, if not successfully delete source files.
     This means probably wrong download, so download should restart'''
    file_names = paths.get_download_filenames(asset_data)
    utils.p('try to append already existing asset')

    if len(file_names) == 0 or not os.path.isfile(file_names[-1]):
        return False

    kwargs['name'] = asset_data['name']
    try:
        append_asset(asset_data, **kwargs)
        if asset_data['asset_type'] == 'scene':
            if bpy.context.scene.hana3d_scene.merge_add == 'ADD':
                for window in bpy.context.window_manager.windows:
                    window.scene = bpy.data.scenes[asset_data['name']]
        return True
    except Exception as e:
        print(e)
        for f in file_names:
            try:
                os.remove(f)
            except Exception:
                e = sys.exc_info()[0]
                print(e)
                pass
        return False


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


def fprint(text):
    print('###################################################################################')
    print('\n\n\n')
    print(text)
    print('\n\n\n')
    print('###################################################################################')


def get_download_url(asset_data, tcom=None):
    ''''retrieves the download url. The server checks if user can download the item.'''
    headers = utils.get_headers()

    r = None

    try:
        r = rerequests.get(asset_data['download_url'], headers=headers)
    except Exception as e:
        print(e)
        if tcom is not None:
            tcom.error = True
    if r is None:
        if tcom is not None:
            tcom.report = 'Connection Error'
            tcom.error = True
        return 'Connection Error'

    if r.status_code < 400:
        data = r.json()
        url = data['filePath']
        asset_data['download_url'] = url
        asset_data['file_name'] = paths.extract_filename_from_url(url)
        return True

    elif r.status_code >= 500:
        utils.p(r.text)
        if tcom is not None:
            tcom.report = 'Server error'
            tcom.error = True
    return False


def start_download(asset_data, **kwargs):
    '''
    check if file isn't downloading or doesn't exist, then start new download
    '''
    downloading = check_downloading(asset_data, **kwargs)
    if downloading:
        return

    fexists = check_existing(asset_data)
    asset_in_scene = check_asset_in_scene(asset_data)

    if fexists and asset_in_scene:
        done = try_finished_append(asset_data, **kwargs)
        if done:
            return

    if asset_data['asset_type'] in ('model', 'material'):
        downloader = {
            'location': kwargs['model_location'],
            'rotation': kwargs['model_rotation'],
        }
        download(asset_data, downloaders=[downloader], **kwargs)

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

    thread_index: IntProperty(
        name="Thread index",
        description='index of the thread to kill',
        default=-1
    )

    def execute(self, context):
        global download_threads
        td = download_threads[self.thread_index]
        download_threads.remove(td)
        td[0].stop()
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

    # @classmethod
    # def poll(cls, context):
    #     return bpy.context.window_manager.Hana3DModelThumbnails is not ''

    def execute(self, context):
        s = bpy.context.scene
        sr = s['search results']

        asset_data = sr[
            self.asset_index
        ].to_dict()  # TODO CHECK ALL OCCURRENCES OF PASSING BLENDER ID PROPS TO THREADS!
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


classes = (
    Hana3DDownloadOperator,
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
