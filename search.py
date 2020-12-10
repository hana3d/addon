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
import os
import threading
import time

import bpy
import requests
from bpy.props import BoolProperty, StringProperty
from bpy.types import Operator

from . import colors, hana3d_oauth, logger, paths, rerequests, utils, ui
from .config import HANA3D_DESCRIPTION, HANA3D_NAME, HANA3D_UI
from .report_tools import execute_wrapper
from .src.preferences.preferences import Preferences
from .src.search.asset_search import AssetSearch
from .src.search.query import Query
from .src.search.search import Search

search_start_time = 0
prev_time = 0


def check_errors(rdata):
    if rdata.get('status_code') == 401:
        logging.debug(rdata)
        if rdata.get('code') == 'token_expired':
            user_preferences = bpy.context.preferences.addons[HANA3D_NAME].preferences
            if user_preferences.api_key != '':
                hana3d_oauth.refresh_token(immediate=False)
                return False, rdata.get('description')
            return False, 'Missing or wrong api_key in addon preferences'
    elif rdata.get('status_code') == 403:
        logging.debug(rdata)
        if rdata.get('code') == 'invalid_permissions':
            return False, rdata.get('description')
    return True, ''


search_threads = []
thumb_sml_download_threads = {}
thumb_full_download_threads = {}
reports = ''


first_time = True
last_clipboard = ''


# @bpy.app.handlers.persistent
def timer_update():
    global first_time
    preferences = Preferences().get()
    if first_time:
        first_time = False
        if preferences.show_on_start:
            search()
            preferences.first_run = False
        return 3.0

    if preferences.first_run:
        search()
        preferences.first_run = False

    global search_threads
    if len(search_threads) == 0:
        return 1.0
    if getattr(bpy.context.window_manager, HANA3D_UI).dragging:
        return 0.5
    for thread in search_threads:
        if not thread[0].is_alive():
            search_threads.remove(thread)
            icons_dir = thread[1]
            asset_type = thread[2]

            search_object = Search(bpy.context, asset_type)
            props = search_object.props
            asset_search = AssetSearch(bpy.context, asset_type)
            asset_search.results = []  # noqa : WPS110
            json_filepath = os.path.join(icons_dir, f'{asset_type}_searchresult.json')

            with open(json_filepath, 'r') as data_file:
                rdata = json.load(data_file)

            result_field = []
            ok, error = check_errors(rdata)
            if ok:
                run_assetbar_op = getattr(bpy.ops.object, f'{HANA3D_NAME}_run_assetbar_fix_context')
                run_assetbar_op()
                for r in rdata['results']:
                    if r['assetType'] == asset_type:
                        if len(r['files']) > 0:
                            tname = None
                            allthumbs = []
                            durl, tname = None, None
                            for f in r['files']:
                                if f['fileType'] == 'thumbnail':
                                    tname = paths.extract_filename_from_url(f['fileThumbnailLarge'])
                                    small_tname = paths.extract_filename_from_url(
                                        f['fileThumbnail'],
                                    )
                                    allthumbs.append(tname)

                                tdict = {}
                                for i, t in enumerate(allthumbs):
                                    tdict['thumbnail_%i'] = t
                                if f['fileType'] == 'blend':
                                    durl = f['downloadUrl']
                            if durl:    # noqa: WPS220
                                # Check for assetBaseId for backwards compatibility
                                view_id = r.get('viewId') or r.get('assetBaseId') or ''
                                tooltip = utils.generate_tooltip(
                                    r['name'],
                                    r['description'],
                                )
                                asset_data = {
                                    'thumbnail': tname,
                                    'thumbnail_small': small_tname,
                                    'download_url': durl,
                                    'id': r['id'],
                                    'view_id': view_id,
                                    'name': r['name'],
                                    'asset_type': r['assetType'],
                                    'tooltip': tooltip,
                                    'tags': r['tags'],
                                    'verification_status': r['verificationStatus'],
                                    'author_id': str(r['author']['id']),
                                    'description': r['description'] or '',
                                    'render_jobs': r.get('render_jobs', []),
                                    'workspace': r.get('workspace', ''),
                                }
                                asset_data['downloaded'] = 0

                                if 'metadata' in r and r['metadata'] is not None:
                                    asset_data['metadata'] = r['metadata']
                                if 'created' in r and r['created'] is not None:
                                    asset_data['created'] = r['created']
                                if 'libraries' in r and r['libraries'] is not None:
                                    asset_data['libraries'] = r['libraries']

                                params = utils.params_to_dict(r['parameters'])

                                if asset_type == 'model':
                                    if params.get('boundBoxMinX') is not None:
                                        bbox = {
                                            'bbox_min': (
                                                float(params['boundBoxMinX']),
                                                float(params['boundBoxMinY']),
                                                float(params['boundBoxMinZ']),
                                            ),
                                            'bbox_max': (
                                                float(params['boundBoxMaxX']),
                                                float(params['boundBoxMaxY']),
                                                float(params['boundBoxMaxZ']),
                                            ),
                                        }

                                    else:
                                        bbox = {
                                            'bbox_min': (-0.5, -0.5, 0),
                                            'bbox_max': (0.5, 0.5, 1),
                                        }
                                    asset_data.update(bbox)

                                asset_data.update(tdict)
                                assets_used = bpy.context.window_manager.get(  # noqa : WPS220
                                    f'{HANA3D_NAME}_assets_used', {},
                                )
                                if view_id in assets_used.keys():  # noqa : WPS220
                                    asset_data['downloaded'] = 100  # noqa : WPS220

                                result_field.append(asset_data)  # noqa : WPS220

                asset_search.results = result_field  # noqa : WPS110
                asset_search.results_orig = rdata
                search_object.results = result_field  # noqa : WPS110
                search_object.results_orig = rdata
                load_previews()
                ui_props = getattr(bpy.context.window_manager, HANA3D_UI)
                if len(result_field) < ui_props.scrolloffset:
                    ui_props.scrolloffset = 0
                props.is_searching = False
                props.search_error = False
                text = f'Found {search_object.results_orig["count"]} results. '  # noqa #501
                ui.add_report(text=text)

            else:
                logging.error(error)
                ui.add_report(text=error, color=colors.RED)
                props.search_error = True

            mt('preview loading finished')
    return 0.3 # noqa : WPS432


def load_placeholder_thumbnail(index: int, asset_id: str):
    """Load placeholder thumbnail for assets without one.

    Arguments:
        index: index number of the asset in search results
        asset_id: asset id
    """
    placeholder_path = paths.get_addon_thumbnail_path('thumbnail_notready.png')

    img = bpy.data.images.load(placeholder_path)
    img.name = utils.previmg_name(index)

    hidden_img = bpy.data.images.load(placeholder_path)
    hidden_img.name = f'.{asset_id}'

    fullsize_img = bpy.data.images.load(placeholder_path)
    fullsize_img.name = utils.previmg_name(index, fullsize=True)


def load_previews():
    mappingdict = {
        'MODEL': 'model',
        'SCENE': 'scene',
        'MATERIAL': 'material',
    }
    # FIRST START SEARCH
    props = getattr(bpy.context.window_manager, HANA3D_UI)

    directory = paths.get_temp_dir(f'{mappingdict[props.asset_type]}_search')
    search_object = Search(bpy.context)
    search_results = search_object.results

    if search_results is not None:
        index = 0
        for search_result in search_results:
            if search_result['thumbnail_small'] == '':
                load_placeholder_thumbnail(index, search_result['id'])
                index += 1
                continue

            tpath = os.path.join(directory, search_result['thumbnail_small'])

            iname = utils.previmg_name(index)

            if os.path.exists(tpath):  # sometimes we are unlucky...
                img = bpy.data.images.get(iname)
                if img is None:
                    img = bpy.data.images.load(tpath)
                    img.name = iname
                elif img.filepath != tpath:
                    # had to add this check for autopacking files...
                    if img.packed_file is not None:
                        img.unpack(method='USE_ORIGINAL')
                    img.filepath = tpath
                    img.reload()
                img.colorspace_settings.name = 'Linear'
            index += 1


class ThumbDownloader(threading.Thread):
    query = None

    def __init__(self, url, path):
        super(ThumbDownloader, self).__init__()
        self.url = url
        self.path = path
        self._stop_event = threading.Event()

    def stop(self):
        self._stop_event.set()

    def stopped(self):
        return self._stop_event.is_set()

    def run(self):
        r = rerequests.get(self.url, stream=False)
        if r.status_code == 200:
            with open(self.path, 'wb') as f:
                f.write(r.content)
            # ORIGINALLY WE DOWNLOADED THUMBNAILS AS STREAM, BUT THIS WAS TOO SLOW.
            # with open(path, 'wb') as f:
            #     for chunk in r.iter_content(1048576*4):
            #         f.write(chunk)


class Searcher(threading.Thread):
    query = None

    def __init__(self, query: Query, params):  # noqa : D107,WPS110
        super(Searcher, self).__init__()
        self.query = query
        self.params = params
        self._stop_event = threading.Event()

    def stop(self):
        self._stop_event.set()

    def stopped(self):
        return self._stop_event.is_set()

    def run(self):
        maxthreads = 50
        query = self.query
        params = self.params

        mt('search thread started')
        tempdir = paths.get_temp_dir(f'{query.asset_type}_search')
        json_filepath = os.path.join(tempdir, f'{query.asset_type}_searchresult.json')

        headers = rerequests.get_headers()

        rdata = {}
        rdata['results'] = []

        if params['get_next']:
            with open(json_filepath, 'r') as infile:
                try:
                    origdata = json.load(infile)
                    urlquery = origdata['next']
                    urlquery = urlquery.replace('False', 'false').replace('True', 'true')
                    # rparameters = {}
                    if urlquery is None:
                        return
                except Exception:
                    # in case no search results found on drive we don't do next page loading.
                    params['get_next'] = False
        if not params['get_next']:
            query.save_last_query()
            urlquery = paths.get_api_url('search', query=self.query)

        search_object = Search(bpy.context)
        search_props = search_object.props
        try:
            logging.debug(urlquery)
            r = rerequests.get(urlquery, headers=headers)
        except requests.exceptions.RequestException as e:
            logging.error(e)
            ui.add_report(text=str(e))
            return
        mt('response is back ')
        try:
            rdata = r.json()
            rdata['status_code'] = r.status_code
        except Exception as inst:
            logging.error(inst)
            ui.add_report(text=r.text)

        mt('data parsed ')

        if self.stopped():
            logging.debug(f'stopping search : {str(query)}')
            return

        mt('search finished')
        i = 0

        thumb_small_urls = []
        thumb_small_filepaths = []
        thumb_full_urls = []
        thumb_full_filepaths = []
        # END OF PARSING
        for d in rdata.get('results', []):
            for f in d['files']:
                # TODO move validation of published assets to server, too manmy checks here.
                if (
                    f['fileType'] == 'thumbnail'
                    and f['fileThumbnail'] is not None
                    and f['fileThumbnailLarge'] is not None
                ):
                    if f['fileThumbnail'] is None:
                        f['fileThumbnail'] = 'NONE'
                    if f['fileThumbnailLarge'] is None:
                        f['fileThumbnailLarge'] = 'NONE'

                    thumb_small_urls.append(f['fileThumbnail'])
                    thumb_full_urls.append(f['fileThumbnailLarge'])

                    imgname = paths.extract_filename_from_url(f['fileThumbnail'])
                    imgpath = os.path.join(tempdir, imgname)
                    thumb_small_filepaths.append(imgpath)

                    imgname = paths.extract_filename_from_url(f['fileThumbnailLarge'])
                    imgpath = os.path.join(tempdir, imgname)
                    thumb_full_filepaths.append(imgpath)

        sml_thbs = zip(thumb_small_filepaths, thumb_small_urls)
        full_thbs = zip(thumb_full_filepaths, thumb_full_urls)

        # we save here because a missing thumbnail check is in the previous loop
        # we can also prepend previous results. These have downloaded thumbnails already...
        if params['get_next']:
            rdata['results'][0:0] = origdata['results']

        with open(json_filepath, 'w') as outfile:
            json.dump(rdata, outfile)

        killthreads_sml = []
        for k in thumb_sml_download_threads.keys():
            if k not in thumb_small_filepaths:
                killthreads_sml.append(k)  # do actual killing here?

        killthreads_full = []
        for k in thumb_full_download_threads.keys():
            if k not in thumb_full_filepaths:
                killthreads_full.append(k)  # do actual killing here?
        # TODO do the killing/ stopping here! remember threads might have finished inbetween!

        if self.stopped():
            logging.debug(f'stopping search : {str(query)}')
            return

        # this loop handles downloading of small thumbnails
        for imgpath, url in sml_thbs:
            if imgpath not in thumb_sml_download_threads and not os.path.exists(imgpath):
                thread = ThumbDownloader(url, imgpath)
                # thread = threading.Thread(target=download_thumbnail, args=([url, imgpath]),
                #                           daemon=True)
                thread.start()
                thumb_sml_download_threads[imgpath] = thread
                # threads.append(thread)

                if len(thumb_sml_download_threads) > maxthreads:
                    while len(thumb_sml_download_threads) > maxthreads:
                        # because for loop can erase some of the items.
                        threads_copy = thumb_sml_download_threads.copy()
                        for tk, thread in threads_copy.items():
                            if not thread.is_alive():
                                thread.join()
                                del thumb_sml_download_threads[tk]
                                i += 1
        if self.stopped():
            logging.debug(f'stopping search : {str(query)}')
            return

        while len(thumb_sml_download_threads) > 0:
            # because for loop can erase some of the items.
            threads_copy = thumb_sml_download_threads.copy()
            for tk, thread in threads_copy.items():
                if not thread.is_alive():
                    thread.join()
                    del thumb_sml_download_threads[tk]
                    i += 1

        if self.stopped():
            logging.debug(f'stopping search : {str(query)}')
            return

        # start downloading full thumbs in the end
        for imgpath, url in full_thbs:
            if imgpath not in thumb_full_download_threads and not os.path.exists(imgpath):
                thread = ThumbDownloader(url, imgpath)
                # thread = threading.Thread(target=download_thumbnail, args=([url, imgpath]),
                #                           daemon=True)
                thread.start()
                thumb_full_download_threads[imgpath] = thread
        mt('thumbnails finished')


def mt(text):
    global search_start_time, prev_time
    alltime = time.time() - search_start_time
    since_last = time.time() - prev_time
    prev_time = time.time()
    logging.debug(f'{text} {alltime} {since_last}')


def add_search_process(query: Query, params):  # noqa : D103,WPS110
    global search_threads

    while len(search_threads) > 0:
        old_thread = search_threads.pop(0)
        old_thread[0].stop()
        # TODO CARE HERE FOR ALSO KILLING THE THREADS...
        # AT LEAST NOW SEARCH DONE FIRST WON'T REWRITE AN OLDER ONE

    tempdir = paths.get_temp_dir(f'{query.asset_type}_search')
    thread = Searcher(query, params)
    thread.start()

    search_threads.append([thread, tempdir, query.asset_type])

    mt('thread started')


def search(get_next=False, author_id=''):
    ''' initialize searching'''
    global search_start_time

    search_start_time = time.time()
    # mt('start')

    search_object = Search(bpy.context)
    search_props = search_object.props

    query = Query(bpy.context, search_props)

    uiprops = getattr(bpy.context.window_manager, HANA3D_UI)
    query.asset_type = uiprops.asset_type.lower()

    if search_props.is_searching and get_next:
        return

    search_props.is_searching = True

    params = {'get_next': get_next}

    add_search_process(query, params)
    ui.add_report(text=f'{HANA3D_DESCRIPTION} searching...', timeout=2)


class SearchOperator(Operator):
    """Tooltip"""

    bl_idname = f'view3d.{HANA3D_NAME}_search'
    bl_label = f'{HANA3D_DESCRIPTION} asset search'
    bl_description = 'Search online for assets'
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}
    own: BoolProperty(name='own assets only', description='Find all own assets', default=False)

    author_id: StringProperty(
        name='Author ID',
        description='Author ID - search only assets by this author',
        default='',
        options={'SKIP_SAVE'},
    )

    get_next: BoolProperty(
        name='next page',
        description='get next page from previous search',
        default=False,
        options={'SKIP_SAVE'},
    )

    keywords: StringProperty(
        name='Keywords',
        description='Keywords',
        default='',
        options={'SKIP_SAVE'},
    )

    @classmethod
    def poll(cls, context):
        return True

    @execute_wrapper
    def execute(self, context):
        # TODO this should all get transferred to properties of the search operator,
        #  so search_props don't have to be fetched here at all.
        search_object = Search(context)
        search_props = search_object.props
        if self.author_id != '':
            search_props.search_keywords = ''
        if self.keywords != '':
            search_props.search_keywords = self.keywords

        search(get_next=self.get_next, author_id=self.author_id)
        # asset_bar_op = getattr(bpy.ops.view3d, f'{HANA3D_NAME}_asset_bar')
        # asset_bar_op()

        return {'FINISHED'}


classes = [SearchOperator]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
