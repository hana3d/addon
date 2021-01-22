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
import copy
import functools
import json
import logging
import os
import shutil
import threading
from dataclasses import asdict
from queue import Queue

import bpy
import requests
from bpy.app.handlers import persistent
from bpy.props import (
    BoolProperty,
    EnumProperty,
    FloatProperty,
    FloatVectorProperty,
    IntProperty,
    StringProperty,
)

from .downloader import Downloader
from .lib import check_existing
from ..async_loop import ensure_async_loop
from ..preferences.profile import update_libraries_list, update_tags_list
from ..search.query import Query
from ..search.search import SearchResult, get_search_results
from ..ui import colors
from ..ui.main import UI
from ...config import (
    HANA3D_DESCRIPTION,
    HANA3D_MODELS,
    HANA3D_NAME,
    HANA3D_SCENES,
)
from ...report_tools import execute_wrapper

from ... import append_link, hana3d_types, logger, paths, render_tools, utils  # noqa E501 isort:skip


download_threads = {}
append_tasks_queue: 'Queue[functools.partial]' = Queue()


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


def get_used_libs() -> set:
    """Get used libs.

    Returns:
        set: Set of used libraries
    """
    used_libs = set()
    for ob in bpy.data.objects:
        if ob.instance_collection is not None and ob.instance_collection.library is not None:
            used_libs.add(ob.instance_collection.library)

        for ps in ob.particle_systems:
            if ps.settings.render_type == 'GROUP' and ps.settings.instance_collection is not None:
                used_libs.add(ps.settings.instance_collection.library)

    return used_libs


def check_unused():
    """Find assets that have been deleted from scene but their library is still present."""
    used_libs = get_used_libs()

    for library in bpy.data.libraries:
        if library not in used_libs:
            logging.info(f'Attempt to remove this library: {library.filepath}')
            # have to unlink all groups, since the file is a 'user'
            # even if the groups aren't used at all...
            for user_id in library.users_id:
                if type(user_id) == bpy.types.Collection:
                    bpy.data.collections.remove(user_id)
            library.user_clear()


@persistent
def scene_save(context):
    ''' does cleanup of Hana3D props and sends a message to the server about assets used.'''
    # TODO this can be optimized by merging these 2 functions, since both iterate over all objects.
    if not bpy.app.background:
        check_unused()


@persistent
def scene_load(context):
    '''restart broken downloads on scene load'''
    global download_threads
    download_threads = {}

    check_missing()


def set_thumbnail(asset_data, asset):
    if asset_data.thumbnail == '':
        asset_props = getattr(asset, HANA3D_NAME)
        asset_props.thumbnail = ''
    else:
        thumbnail_name = asset_data.thumbnail.split(os.sep)[-1]  # noqa: WPS204
        tempdir = paths.get_temp_dir(f'{asset_data.asset_type}_search')  # noqa: WPS204
        thumbpath = os.path.join(tempdir, thumbnail_name)
        asset_thumbs_dir = paths.get_download_dirs(asset_data.asset_type)[0]
        asset_thumb_path = os.path.join(asset_thumbs_dir, thumbnail_name)
        shutil.copy(thumbpath, asset_thumb_path)
        asset_props = getattr(asset, HANA3D_NAME)
        asset_props.thumbnail = asset_thumb_path


def update_downloaded_progress(downloader: Downloader):
    """Update download progress.

    Parameters:
        downloader: Downloader class
    """
    search_results = get_search_results()
    if search_results is None:
        logging.debug('Empty search results')  # noqa : WPS421:230
        return
    for search_result in search_results:
        if search_result.view_id == downloader.asset_data.view_id:
            search_result.downloaded = downloader.progress()
            return


def remove_file(filepath):
    try:
        os.remove(filepath)
    except Exception as e:
        logging.error(f'Error when removing {filepath}: {e}')


def process_finished_thread(downloader: Downloader):
    asset_data = downloader.asset_data

    file_names = paths.get_download_filenames(asset_data)
    # duplicate file if the global and subdir are used in prefs
    # todo this should try to check if both files exist and are ok.
    if len(file_names) == 2:
        shutil.copyfile(file_names[0], file_names[1])

    if downloader.passargs.get('redownload'):
        # handle lost libraries here:
        for library in bpy.data.libraries:
            if (
                library.get('asset_data') is not None
                and library['asset_data']['view_id'] == asset_data.view_id
            ):
                library.filepath = file_names[-1]
                library.reload()
        return
    append_asset_safe(asset_data, **downloader.passargs)


def execute_append_tasks():
    if append_tasks_queue.empty():
        return 0.5
    if any(thread.is_alive() for thread in download_threads.values()):
        return 0.1

    task = append_tasks_queue.get()
    try:
        task()
        append_tasks_queue.task_done()
    except Exception as e:
        asset_data, = task.args
        file_names = file_names = paths.get_download_filenames(asset_data)
        for f in file_names:
            remove_file(f)
        ui = UI()
        ui.add_report(f'Error when appending {asset_data.name} to scene: {e}', color=colors.RED)

        # cleanup failed downloads
        file_names = paths.get_download_filenames(asset_data)
        for file_name in file_names:
            remove_file(file_name)
        download_kill_op = getattr(bpy.ops.scene, f'{HANA3D_NAME}_download_kill')
        download_kill_op(view_id=asset_data.view_id)
    return 0.01


# @bpy.app.handlers.persistent
def timer_update():  # TODO might get moved to handle all hana3d stuff, not to slow down.
    '''check for running and finished downloads and react. write progressbars too.'''
    if len(download_threads) == 0:
        return 1.0
    for view_id, downloader in download_threads.items():
        if downloader.finished:
            # Ignore download theads that are finished but the asset was not appended
            continue
        asset_data = downloader.asset_data
        if downloader.is_alive():
            update_downloaded_progress(downloader)
            continue

        if bpy.context.mode == 'EDIT' and asset_data.asset_type in {'model', 'material'}:
            continue

        downloader.set_progress(100)
        update_downloaded_progress(downloader)
        process_finished_thread(downloader)
        downloader.finished = True

    return 0.1


def download(asset_data, **kwargs):
    '''start the download thread'''

    # incoming data can be either directly dict from python, or blender id property
    # (recovering failed downloads on reload)
    if type(asset_data) == dict:
        asset_data = SearchResult(**asset_data)

    logging.debug(f'Downloading asset_data {json.dumps(asdict(asset_data))}')
    thread = Downloader(asset_data, **kwargs)
    thread.start()

    view_id = asset_data.view_id
    download_threads[view_id] = thread


def add_import_params(thread: Downloader, location, rotation):
    params = {
        'location': location,
        'rotation': rotation,
    }
    thread.passargs['import_params'].append(params)


def import_scene(asset_data: SearchResult, file_names: list):
    """
    Import scene.

    Parameters:
        asset_data: scene info
        file_names: list of filenames

    Returns:
        linked scene
    """
    scene = append_link.append_scene(file_names[0], link=False, fake_user=False)
    scene.name = asset_data.name
    props = getattr(bpy.context.window_manager, HANA3D_SCENES)
    if props.merge_add == 'ADD':
        for window in bpy.context.window_manager.windows:
            window.scene = bpy.data.scenes[asset_data.name]
    return scene


def _import_model_with_params(asset_data: SearchResult, file_name: str, link: bool, **kwargs):
    for import_param in kwargs['import_params']:
        if link is True:
            parent, newobs = append_link.link_collection(
                file_name,
                location=import_param['location'],
                rotation=import_param['rotation'],
                link=link,
                name=asset_data.name,
                parent=kwargs.get('parent'),
            )
        else:
            parent, newobs = append_link.append_objects(
                file_name,
                location=import_param['location'],
                rotation=import_param['rotation'],
                link=link,
                name=asset_data.name,
                parent=kwargs.get('parent'),
            )

        if parent.type == 'EMPTY' and link:
            bmin = asset_data.bbox_min
            bmax = asset_data.bbox_max
            size_min = min(
                1.0,
                (bmax[0] - bmin[0] + bmax[1] - bmin[1] + bmax[2] - bmin[2]) / 3,  # noqa : WPS221
            )
            parent.empty_display_size = size_min
    return parent


def _import_model_with_location(asset_data: SearchResult, file_name: str, link: bool, **kwargs):
    if link is True:
        parent, newobs = append_link.link_collection(
            file_name,
            location=kwargs['model_location'],
            rotation=kwargs['model_rotation'],
            link=link,
            name=asset_data.name,
            parent=kwargs.get('parent'),
        )
    else:
        parent, newobs = append_link.append_objects(
            file_name,
            location=kwargs['model_location'],
            rotation=kwargs['model_rotation'],
            link=link,
            parent=kwargs.get('parent'),
        )
    if parent.type == 'EMPTY' and link:
        bmin = asset_data.bbox_min
        bmax = asset_data.bbox_max
        size_min = min(1.0, (bmax[0] - bmin[0] + bmax[1] - bmin[1] + bmax[2] - bmin[2]) / 3)
        parent.empty_display_size = size_min
    return parent


def import_model(window_manager, asset_data: SearchResult, file_names: list, **kwargs):
    """Import model to scene.

    Parameters:
        window_manager: Blender window manager
        asset_data: Asset Data
        file_names: list of files
        kwargs: keyword arguments

    Returns:
        Parent of the imported object
    """
    sprops = getattr(window_manager, HANA3D_MODELS)
    if sprops.append_method == 'LINK_COLLECTION':
        sprops.append_link = 'LINK'
        sprops.import_as = 'GROUP'
    else:
        sprops.append_link = 'APPEND'
        sprops.import_as = 'INDIVIDUAL'

    append_or_link = sprops.append_link
    asset_in_scene = check_asset_in_scene(asset_data)
    link = (asset_in_scene == 'LINK') or (append_or_link == 'LINK')

    if kwargs.get('import_params'):
        parent = _import_model_with_params(asset_data, file_names[-1], link, **kwargs)

    elif kwargs.get('model_location') is not None:
        parent = _import_model_with_location(asset_data, file_names[-1], link, **kwargs)

    if link:
        group = parent.instance_collection
        lib = group.library
        lib['asset_data'] = asdict(asset_data)

    utils.fill_object_metadata(parent)
    return parent


def import_material(asset_data: SearchResult, file_names: list, **kwargs):
    """Import material.

    Parameters:
        asset_data: material info
        file_names: list of filenames
        kwargs: additional parameters

    Returns:
        imported material
    """
    for mat in bpy.data.materials:
        if getattr(mat, HANA3D_NAME).view_id == asset_data.view_id:
            inscene = True
            material = mat
            break
    else:
        inscene = False
    if not inscene:
        material = append_link.append_material(file_names[-1], link=False, fake_user=False)
    target_object = bpy.data.objects[kwargs['target_object']]

    if len(target_object.material_slots) == 0:
        target_object.data.materials.append(material)
    else:
        target_object.material_slots[kwargs['material_target_slot']].material = material
    return material


def set_library_props(asset_data, asset_props):
    """Set libraries on asset props.

    Parameters:
        asset_data: Asset Data
        asset_props: Asset Props
    """
    update_libraries_list(asset_props, bpy.context)
    libraries_list = asset_props.libraries_list
    for asset_library in asset_data.libraries:
        library = libraries_list[asset_library['name']]
        library.selected = True
        if 'metadata' in asset_library and asset_library['metadata'] is not None:
            for view_prop in library.metadata['view_props']:
                name = f'{library.name} {view_prop["name"]}'
                slug = view_prop['slug']
                if name not in asset_props.custom_props:
                    asset_props.custom_props_info[name] = {
                        'slug': slug,
                        'library_name': library.name,
                        'library_id': library.id_,
                    }
                if 'view_props' in asset_library['metadata'] and slug in asset_library['metadata']['view_props']:  # noqa: E501
                    asset_props.custom_props[name] = asset_library['metadata']['view_props'][slug]
                else:
                    asset_props.custom_props[name] = ''


def set_asset_props(asset, asset_data):
    asset_props = getattr(asset, HANA3D_NAME)
    asset_props.clear_data()
    asset['asset_data'] = asdict(asset_data)

    set_thumbnail(asset_data, asset)

    asset_props.id = asset_data.id  # noqa: WPS125
    asset_props.view_id = asset_data.view_id
    asset_props.view_workspace = asset_data.workspace
    asset_props.name = asset_data.name
    asset_props.tags = ','.join(asset_data.tags)
    asset_props.description = asset_data.description
    asset_props.asset_type = asset_data.asset_type

    jobs = render_tools.get_render_jobs(asset_data.asset_type, asset_data.view_id)
    asset_props.render_data['jobs'] = jobs
    render_tools.update_render_list(asset_props)

    if asset_data.tags:
        update_tags_list(asset_props, bpy.context)
        for tag in asset_data.tags:
            asset_props.tags_list[tag].selected = True

    if asset_data.libraries:
        set_library_props(asset_data, asset_props)


def append_asset(asset_data: SearchResult, **kwargs):
    """Append asset to scene.

    Parameters:
        asset_data: asset info
        kwargs: additional parameters

    Raises:
        FileNotFoundError: when the asset file is not found
    """
    asset_name = asset_data.name
    logging.debug(f'Appending asset {asset_name}')

    file_names = paths.get_download_filenames(asset_data)
    if not file_names or not os.path.isfile(file_names[-1]):
        raise FileNotFoundError(f'Could not find file for asset {asset_name}')

    kwargs['name'] = asset_name
    wm = bpy.context.window_manager

    if asset_data.asset_type == 'scene':
        asset = import_scene(asset_data, file_names)
    if asset_data.asset_type == 'model':
        asset = import_model(wm, asset_data, file_names, **kwargs)
    elif asset_data.asset_type == 'material':
        asset = import_material(asset_data, file_names, **kwargs)

    wm[f'{HANA3D_NAME}_assets_used'] = wm.get(f'{HANA3D_NAME}_assets_used', {})
    wm[f'{HANA3D_NAME}_assets_used'][asset_data.view_id] = asdict(asset_data)

    set_asset_props(asset, asset_data)

    if asset_data.view_id in download_threads:
        download_threads.pop(asset_data.view_id)

    undo_push_context_op = getattr(bpy.ops.wm, f'{HANA3D_NAME}_undo_push_context')
    undo_push_context_op(message=f'add {asset_data.name} to scene')


def append_asset_safe(asset_data: SearchResult, **kwargs):
    """Safely append asset.

    Creates append task and adds it to the task queue.

    Parameters:
        asset_data: asset data
        kwargs: additional parameters
    """
    task = functools.partial(append_asset, asset_data, **kwargs)
    append_tasks_queue.put(task)


def check_asset_in_scene(asset_data: SearchResult) -> str:
    """Check if asset is already in scene.

    If it is, modifies asset data so it can be reached again.

    Parameters:
        asset_data: asset data

    Returns:
        'LINK' or 'APPEND'
    """
    wm = bpy.context.window_manager
    assets_used = wm.get(f'{HANA3D_NAME}_assets_used', {})

    view_id = asset_data.view_id
    if view_id in assets_used.keys():
        ad = assets_used[id]
        if ad.get('file_name') is not None:

            asset_data.file_name = ad['file_name']
            asset_data.download_url = ad['download_url']

            collection = bpy.data.collections.get(ad['name'])
            if collection is not None:
                if collection.users > 0:
                    return 'LINK'
            return 'APPEND'
    return ''


def start_download(asset_data: SearchResult, **kwargs):
    """
    Check if file isn't downloading or doesn't exist, then start new download.

    Parameters:
        asset_data: asset data
        kwargs: additional parameters
    """
    view_id = asset_data.view_id
    if view_id in download_threads and download_threads[view_id].is_alive():
        if asset_data.asset_type in {'model', 'material'}:
            thread = download_threads[view_id]
            add_import_params(thread, kwargs['model_location'], kwargs['model_rotation'])
        return

    fexists = check_existing(asset_data)
    asset_in_scene = check_asset_in_scene(asset_data)

    if fexists and asset_in_scene:
        append_asset_safe(asset_data, **kwargs)
        return

    if asset_data.asset_type in {'model', 'material'}:
        transform = {
            'location': kwargs['model_location'],
            'rotation': kwargs['model_rotation'],
        }
        download(asset_data, import_params=[transform], **kwargs)

    elif asset_data.asset_type == 'scene':
        download(asset_data, **kwargs)


asset_types = (
    ('MODEL', 'Model', 'set of objects'),
    ('SCENE', 'Scene', 'scene'),
    ('MATERIAL', 'Material', 'any .blend Material'),
    ('ADDON', 'Addon', 'addnon'),
)


class Hana3DKillDownloadOperator(bpy.types.Operator):
    """Kill a download"""

    bl_idname = f'scene.{HANA3D_NAME}_download_kill'
    bl_label = f'{HANA3D_DESCRIPTION} Kill Asset Download'
    bl_options = {'REGISTER', 'INTERNAL'}

    view_id: StringProperty()  # type: ignore

    @execute_wrapper
    def execute(self, context):
        thread = download_threads.pop(self.view_id)
        thread.stop()

        tasks = []
        while not append_tasks_queue.empty():
            task = append_tasks_queue.get()
            if task.args[0]['view_id'] == self.view_id:
                del task
                break
            tasks.append(task)
        for task in tasks:
            append_tasks_queue.put(task)
        return {'FINISHED'}


class Hana3DDownloadOperator(bpy.types.Operator):
    """Download and link asset to scene. Only link if asset already available locally."""

    bl_idname = f'scene.{HANA3D_NAME}_download'
    bl_label = f'{HANA3D_DESCRIPTION} Asset Download'
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    asset_type: EnumProperty(  # type: ignore
        name='Type',
        items=asset_types,
        description='Type of download',
        default='MODEL',
    )
    asset_index: IntProperty(  # type: ignore
        name='Asset Index',
        description='asset index in search results',
        default=-1,
    )

    target_object: StringProperty(  # type: ignore
        name='Target Object',
        description='Material or object target for replacement',
        default='',
    )

    material_target_slot: IntProperty(  # type: ignore
        name='Asset Index',
        description='asset index in search results',
        default=0,
    )
    model_location: FloatVectorProperty(name='Asset Location', default=(0, 0, 0))  # type: ignore
    model_rotation: FloatVectorProperty(name='Asset Rotation', default=(0, 0, 0))  # type: ignore

    replace: BoolProperty(  # type: ignore
        name='Replace',
        description='replace selection with the asset',
        default=False,
    )

    cast_parent: StringProperty(  # type: ignore
        name='Particles Target Object',
        description='',
        default='',
    )

    @execute_wrapper
    def execute(self, context):
        """Download execute.

        Parameters:
            context: Blender context

        Returns:
            enum set in {‘RUNNING_MODAL’, ‘CANCELLED’, ‘FINISHED’}
        """
        search_results = get_search_results()

        # TODO CHECK ALL OCCURRENCES OF PASSING BLENDER ID PROPS TO THREADS!
        asset_data = search_results[self.asset_index]
        assets_used = context.window_manager.get(f'{HANA3D_NAME}_assets_used')
        if assets_used is None:
            context.window_manager[f'{HANA3D_NAME}_assets_used'] = {}

        atype = asset_data.asset_type
        if (  # noqa: WPS337
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


class Hana3DBatchDownloadOperator(bpy.types.Operator):  # noqa : WPS338
    """Download and link all searched preview assets to scene."""

    bl_idname = f'scene.{HANA3D_NAME}_batch_download'
    bl_label = f'{HANA3D_DESCRIPTION} Batch Download'
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    object_count: IntProperty(  # type: ignore
        name='Object Count',
        description='number of objects imported to scene',
        default=0,
        options={'HIDDEN'},
    )

    last_query: StringProperty(  # type: ignore
        name='Last Searched Query',
        description='string representing the last performed query',
        default='',
        options={'HIDDEN'},
    )

    grid_distance: FloatProperty(  # type: ignore
        name='Grid Distance',
        description='distance between objects on the grid',
        precision=1,
        step=0.5,
        default=3,
    )

    batch_size: IntProperty(  # type: ignore
        name='Batch Size',
        description='number of objects to download in parallel',
        default=20,  # noqa : WPS432
    )

    def _get_location(self):
        pos_x, pos_y = 0
        dx = 0
        dy = -1
        for _ in range(self.object_count):  # noqa : WPS122
            if pos_x == pos_y or (pos_x < 0 and pos_x == -pos_y) or (pos_x > 0 and pos_x == 1 - pos_y):  # noqa : WPS220,WPS221
                dx = -dy
                dy = dx
            pos_x, pos_y = pos_x + dx, pos_y + dy
        self.object_count += 1
        return (self.grid_distance * pos_x, self.grid_distance * pos_y, 0)

    @classmethod
    def poll(cls, context):
        """Batch download poll.

        Parameters:
            context: Blender context

        Returns:
            bool: existence of download threads running
        """
        return not download_threads

    @execute_wrapper
    def execute(self, context):
        """Execute batch download operator.

        Parameters:
            context: Blender context

        Returns:
            enum set in {‘RUNNING_MODAL’, ‘CANCELLED’, ‘FINISHED’}
        """
        search_results = get_search_results()
        ui = UI()
        if not search_results:
            ui.add_report('Empty search results')
            return {'CANCELLED'}

        query = Query(context)
        last_query = query.get_last_query()

        if last_query != self.last_query:
            self.object_count = 0
            self.last_query = last_query

        n_assets_to_download = min(self.batch_size, len(search.results) - self.object_count)
        if n_assets_to_download == 0:
            ui.add_report('Fetch more results to continue downloading')
        else:
            ui.add_report(f'Downloading {n_assets_to_download} assets')

        ensure_async_loop()
        for _, asset_data in zip(  # noqa : WPS352
            range(self.batch_size),
            search.get_search_results()[self.object_count:],
        ):
            location = self._get_location()
            kwargs = {
                'cast_parent': '',
                'target_object': '',
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
    Hana3DKillDownloadOperator,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.app.handlers.load_post.append(scene_load)
    bpy.app.handlers.save_pre.append(scene_save)

    bpy.app.timers.register(timer_update)
    bpy.app.timers.register(execute_append_tasks)


def unregister():
    if bpy.app.timers.is_registered(execute_append_tasks):
        bpy.app.timers.unregister(execute_append_tasks)
    if bpy.app.timers.is_registered(timer_update):
        bpy.app.timers.unregister(timer_update)

    bpy.app.handlers.save_pre.remove(scene_save)
    bpy.app.handlers.load_post.remove(scene_load)

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
