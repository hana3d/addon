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

    hana3d_oauth = reload(hana3d_oauth)
    paths = reload(paths)
    rerequests = reload(rerequests)
    tasks_queue = reload(tasks_queue)
    ui = reload(ui)
    utils = reload(utils)
else:
    from hana3d import hana3d_oauth, paths, rerequests, tasks_queue, ui, utils

import json
import os
import platform
import threading
import time

import bpy
import requests
from bpy.app.handlers import persistent
from bpy.props import BoolProperty, StringProperty
from bpy.types import Operator

search_start_time = 0
prev_time = 0


def check_errors(rdata):
    if rdata.get('status_code') == 401:
        utils.p(rdata)
        if rdata.get('code') == 'token_expired':
            user_preferences = bpy.context.preferences.addons['hana3d'].preferences
            if user_preferences.api_key != '':
                hana3d_oauth.refresh_token_thread()
                return False, rdata.get('description')
            return False, 'Missing or wrong api_key in addon preferences'
    return True, ''


search_threads = []
thumb_sml_download_threads = {}
thumb_full_download_threads = {}
reports = ''


def refresh_token_timer():
    ''' this timer gets run every time the token needs refresh. '''
    utils.p('refresh timer')
    user_preferences = bpy.context.preferences.addons['hana3d'].preferences
    fetch_server_data()

    return user_preferences.api_key_life


@persistent
def scene_load(context):
    if not bpy.app.timers.is_registered(refresh_token_timer):
        bpy.app.timers.register(refresh_token_timer)


def fetch_server_data():
    if not bpy.app.background:
        user_preferences = bpy.context.preferences.addons['hana3d'].preferences
        api_key = user_preferences.api_key
        # Only refresh new type of tokens(by length), and only one hour before the token timeouts.
        if (
            len(user_preferences.api_key) > 0
            and user_preferences.api_key_timeout < time.time()
        ):
            hana3d_oauth.refresh_token_thread()
        if api_key != '' and bpy.context.window_manager.get('hana3d profile') is None:
            get_profile()


first_time = True
last_clipboard = ''


def check_clipboard():
    # clipboard monitoring to search assets from web
    if platform.system() != 'Linux':
        global last_clipboard
        if bpy.context.window_manager.clipboard != last_clipboard:
            last_clipboard = bpy.context.window_manager.clipboard
            instr = 'view_id:'
            # first check if contains asset id, then asset type
            if last_clipboard[: len(instr)] == instr:
                atstr = 'asset_type:'
                ati = last_clipboard.find(atstr)
                # this only checks if the asset_type keyword is there but
                # let's the keywords update function do the parsing.
                if ati > -1:
                    search_props = utils.get_search_props()
                    search_props.search_keywords = last_clipboard
                    # don't run search after this
                    # assigning to keywords runs the search_update function.


# @bpy.app.handlers.persistent
def timer_update():
    global first_time
    preferences = bpy.context.preferences.addons['hana3d'].preferences
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
    if bpy.context.scene.Hana3DUI.dragging:
        return 0.5
    for thread in search_threads:
        if not thread[0].is_alive():
            search_threads.remove(thread)  #
            icons_dir = thread[1]
            scene = bpy.context.scene
            s = bpy.context.scene
            asset_type = thread[2]
            if asset_type == 'model':
                props = scene.hana3d_models
                json_filepath = os.path.join(icons_dir, 'model_searchresult.json')
                search_name = 'hana3d model search'
            if asset_type == 'scene':
                props = scene.hana3d_scene
                json_filepath = os.path.join(icons_dir, 'scene_searchresult.json')
                search_name = 'hana3d scene search'
            if asset_type == 'material':
                props = scene.hana3d_mat
                json_filepath = os.path.join(icons_dir, 'material_searchresult.json')
                search_name = 'hana3d material search'

            s[search_name] = []

            global reports
            if reports != '':
                props.report = str(reports)
                return 0.2
            with open(json_filepath, 'r') as data_file:
                rdata = json.load(data_file)

            result_field = []
            ok, error = check_errors(rdata)
            if ok:
                bpy.ops.object.run_assetbar_fix_context()
                for r in rdata['results']:
                    try:
                        r['filesSize'] = int(r['filesSize'] / 1024)
                    except Exception:
                        utils.p('asset with no files-size')
                    if r['assetType'] == asset_type:
                        if len(r['files']) > 0:
                            tname = None
                            allthumbs = []
                            durl, tname = None, None
                            for f in r['files']:
                                if f['fileType'] == 'thumbnail':
                                    tname = paths.extract_filename_from_url(f['fileThumbnailLarge'])
                                    small_tname = paths.extract_filename_from_url(
                                        f['fileThumbnail']
                                    )
                                    allthumbs.append(tname)

                                tdict = {}
                                for i, t in enumerate(allthumbs):
                                    tdict['thumbnail_%i'] = t
                                if f['fileType'] == 'blend':
                                    durl = f['downloadUrl']
                            if durl and tname:
                                # Check for assetBaseId for backwards compatibility
                                view_id = r.get('viewId') or r.get('assetBaseId') or ''
                                tooltip = generate_tooltip(r)
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
                                    'render_jobs': r.get('render_jobs', [])
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
                                if view_id in scene.get('assets used', {}).keys():
                                    asset_data['downloaded'] = 100

                                result_field.append(asset_data)

                s[search_name] = result_field
                s['search results'] = result_field
                s[search_name + ' orig'] = rdata
                s['search results orig'] = rdata
                load_previews()
                ui_props = bpy.context.scene.Hana3DUI
                if len(result_field) < ui_props.scrolloffset:
                    ui_props.scrolloffset = 0
                props.is_searching = False
                props.search_error = False
                props.report = 'Found %i results. ' % (s['search results orig']['count'])
                if len(s['search results']) == 0:
                    tasks_queue.add_task((ui.add_report, ('No matching results found.',)))

            else:
                print('error', error)
                props.report = error
                props.search_error = True

            mt('preview loading finished')
    return 0.3


def load_previews():
    mappingdict = {
        'MODEL': 'model',
        'SCENE': 'scene',
        'MATERIAL': 'material',
    }
    scene = bpy.context.scene
    # FIRST START SEARCH
    props = scene.Hana3DUI

    directory = paths.get_temp_dir('%s_search' % mappingdict[props.asset_type])
    s = bpy.context.scene
    results = s.get('search results')
    #
    if results is not None:
        i = 0
        for r in results:

            tpath = os.path.join(directory, r['thumbnail_small'])

            iname = utils.previmg_name(i)

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
            i += 1
    # print('previews loaded')


#  line splitting for longer texts...
def split_subs(text, threshold=40):
    if text == '':
        return []
    # temporarily disable this, to be able to do this in drawing code

    text = text.rstrip()
    text = text.replace('\r\n', '\n')

    lines = []

    while len(text) > threshold:
        # first handle if there's an \n line ending
        i_rn = text.find('\n')
        if 1 < i_rn < threshold:
            i = i_rn
            text = text.replace('\n', '', 1)
        else:
            i = text.rfind(' ', 0, threshold)
            i1 = text.rfind(',', 0, threshold)
            i2 = text.rfind('.', 0, threshold)
            i = max(i, i1, i2)
            if i <= 0:
                i = threshold
        lines.append(text[:i])
        text = text[i:]
    lines.append(text)
    return lines


def list_to_str(input):
    output = ''
    for i, text in enumerate(input):
        output += text
        if i < len(input) - 1:
            output += ', '
    return output


def writeblock(t, input, width=40):  # for longer texts
    dlines = split_subs(input, threshold=width)
    for i, l in enumerate(dlines):
        t += '%s\n' % l
    return t


def writeblockm(tooltip, mdata, key='', pretext=None, width=40):  # for longer texts
    if mdata.get(key) is None:
        return tooltip
    else:
        intext = mdata[key]
        if type(intext) == list:
            intext = list_to_str(intext)
        if type(intext) == float:
            intext = round(intext, 3)
        intext = str(intext)
        if intext.rstrip() == '':
            return tooltip
        if pretext is None:
            pretext = key
        if pretext != '':
            pretext = pretext + ': '
        text = pretext + intext
        dlines = split_subs(text, threshold=width)
        for i, l in enumerate(dlines):
            tooltip += '%s\n' % l

    return tooltip


def fmt_length(prop):
    prop = str(round(prop, 2)) + 'm'
    return prop


def has(mdata, prop):
    if mdata.get(prop) is not None and mdata[prop] is not None and mdata[prop] is not False:
        return True
    else:
        return False


def generate_tooltip(mdata):
    col_w = 40
    if type(mdata['parameters']) == list:
        mparams = utils.params_to_dict(mdata['parameters'])
    else:
        mparams = mdata['parameters']
    t = ''
    t = writeblock(t, mdata['name'], width=col_w)
    t += '\n'

    t = writeblockm(t, mdata, key='description', pretext='', width=col_w)
    if mdata['description'] != '':
        t += '\n'

    t = writeblockm(t, mparams, key='designer', pretext='designer', width=col_w)
    t = writeblockm(t, mparams, key='manufacturer', pretext='manufacturer', width=col_w)
    # t = writeblockm(t, mdata, key='tags', width = col_w)

    if has(mparams, 'dimensionX'):
        t += 'size: %s, %s, %s\n' % (
            fmt_length(mparams['dimensionX']),
            fmt_length(mparams['dimensionY']),
            fmt_length(mparams['dimensionZ']),
        )
    if has(mparams, 'faceCount'):
        t += 'face count: %s, render: %s\n' % (mparams['faceCount'], mparams['faceCountRender'])

    # t = writeblockm(t, mparams, key='objectCount', pretext='nubmber of objects', width = col_w)

    if has(mparams, 'thumbnailScale'):
        t = writeblockm(t, mparams, key='thumbnailScale', pretext='preview scale', width=col_w)

    # generator is for both upload preview and search, this is only after search
    # if mdata.get('versionNumber'):
    #     # t = writeblockm(t, mdata, key='versionNumber', pretext='version', width = col_w)
    #     a_id = mdata['author'].get('id')
    #     if a_id is not None:
    #         adata = bpy.context.window_manager['hana3d authors'].get(str(a_id))
    #         if adata is not None:
    #             t += generate_author_textblock(adata)

    # t += '\n'
    return t


def generate_author_textblock(adata):
    t = '\n\n\n'

    if adata not in (None, ''):
        col_w = 40
        if len(adata['firstName'] + adata['lastName']) > 0:
            t = 'Author:\n'
            t += '%s %s\n' % (adata['firstName'], adata['lastName'])
            t += '\n'
            if adata.get('aboutMeUrl') is not None:
                t = writeblockm(t, adata, key='aboutMeUrl', pretext='', width=col_w)
                t += '\n'
            if adata.get('aboutMe') is not None:
                t = writeblockm(t, adata, key='aboutMe', pretext='', width=col_w)
                t += '\n'
    return t


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


def write_gravatar(a_id, gravatar_path):
    '''
    Write down gravatar path, as a result of thread-based gravatar image download.
    This should happen on timer in queue.
    '''
    # print('write author', a_id, type(a_id))
    authors = bpy.context.window_manager['hana3d authors']
    if authors.get(a_id) is not None:
        adata = authors.get(a_id)
        adata['gravatarImg'] = gravatar_path


def fetch_gravatar(adata):
    utils.p('fetch gravatar')
    if adata.get('gravatarHash') is not None:
        gravatar_url = adata['gravatarHash']
        gravatar_hash = gravatar_url.split('/')[-1].split('.')[0]
        gravatar_path = paths.get_temp_dir(subdir='g/') + gravatar_hash + '.jpg'

        if os.path.exists(gravatar_path):
            tasks_queue.add_task((write_gravatar, (adata['id'], gravatar_path)))
            return

        # url = "https://www.gravatar.com/avatar/" + adata['gravatarHash'] + '?d=404'
        r = rerequests.get(gravatar_url, stream=False)
        if r.status_code == 200:
            with open(gravatar_path, 'wb') as f:
                f.write(r.content)
            tasks_queue.add_task((write_gravatar, (adata['id'], gravatar_path)))
        elif r.status_code == '404':
            adata['gravatarHash'] = None
            utils.p('gravatar for author not available.')


fetching_gravatars = {}


def get_author(r):
    ''' Writes author info (now from search results) and fetches gravatar if needed.'''
    global fetching_gravatars

    a_id = str(r['author']['id'])
    authors = bpy.context.window_manager.get('hana3d authors', {})
    if authors == {}:
        bpy.context.window_manager['hana3d authors'] = authors
    a = authors.get(a_id)
    # or a is '' or (a.get('gravatarHash') is not None and a.get('gravatarImg') is None):
    if a is None:
        a = r['author']
        a['id'] = a_id
        a['tooltip'] = generate_author_textblock(a)

        authors[a_id] = a
        if fetching_gravatars.get(a['id']) is None:
            fetching_gravatars[a['id']] = True

        thread = threading.Thread(target=fetch_gravatar, args=(a.copy(),), daemon=True)
        thread.start()
    return a


def write_profile(adata):
    utils.p('writing profile')
    bpy.context.window_manager['hana3d profile'] = adata


def request_profile():
    a_url = paths.get_api_url('me')
    headers = utils.get_headers(include_id_token=True)
    r = rerequests.get(a_url, headers=headers)
    adata = r.json()
    if adata.get('user') is None:
        utils.p(adata)
        utils.p('getting profile failed')
        return None
    return adata


def fetch_profile():
    utils.p('fetch profile')
    try:
        adata = request_profile()
        if adata is not None:
            tasks_queue.add_task((write_profile, (adata,)))
    except Exception as e:
        utils.p(e)


def get_profile():
    a = bpy.context.window_manager.get('hana3d profile')
    thread = threading.Thread(target=fetch_profile, args=(), daemon=True)
    thread.start()
    return a


class Searcher(threading.Thread):
    query = None

    def __init__(self, query, params):
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
        global reports

        mt('search thread started')
        tempdir = paths.get_temp_dir('%s_search' % query['asset_type'])
        json_filepath = os.path.join(tempdir, '%s_searchresult.json' % query['asset_type'])

        headers = utils.get_headers()

        rdata = {}
        rdata['results'] = []

        if params['get_next']:
            with open(json_filepath, 'r') as infile:
                try:
                    origdata = json.load(infile)
                    urlquery = origdata['next']
                    # rparameters = {}
                    if urlquery is None:
                        return
                except Exception:
                    # in case no search results found on drive we don't do next page loading.
                    params['get_next'] = False
        if not params['get_next']:
            urlquery = paths.get_api_url('search', query=self.query)
        try:
            utils.p(urlquery)
            r = rerequests.get(urlquery, headers=headers)
            # print(r.url)
            reports = ''
            # utils.p(r.text)
        except requests.exceptions.RequestException as e:
            print(e)
            reports = e
            # props.report = e
            return
        mt('response is back ')
        try:
            rdata = r.json()
            rdata['status_code'] = r.status_code
        except Exception as inst:
            reports = r.text
            print(inst)

        mt('data parsed ')

        # print('number of results: ', len(rdata.get('results', [])))
        if self.stopped():
            utils.p('stopping search : ' + str(query))
            return

        mt('search finished')
        i = 0

        thumb_small_urls = []
        thumb_small_filepaths = []
        thumb_full_urls = []
        thumb_full_filepaths = []
        # END OF PARSING
        for d in rdata.get('results', []):

            get_author(d)

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
            utils.p('stopping search : ' + str(query))
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
                                # utils.p(x)
                                del thumb_sml_download_threads[tk]
                                # utils.p('fetched thumbnail ', i)
                                i += 1
        if self.stopped():
            utils.p('stopping search : ' + str(query))
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
            utils.p('stopping search : ' + str(query))
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


def build_query_common(query, props):
    '''add shared parameters to query'''
    query_common = {}
    if props.search_keywords != '':
        query_common['search_term'] = props.search_keywords

    if props.search_verification_status != 'ALL':
        query_common['verification_status'] = props.search_verification_status.lower()

    if props.public_only:
        query['public'] = True

    query.update(query_common)


def build_query_model():
    '''use all search input to request results from server'''

    props = bpy.context.scene.hana3d_models
    query = {
        "asset_type": 'model',
    }

    build_query_common(query, props)

    return query


def build_query_scene():
    '''use all search input to request results from server'''

    props = bpy.context.scene.hana3d_scene
    query = {
        "asset_type": 'scene',
    }
    build_query_common(query, props)
    return query


def build_query_material():
    props = bpy.context.scene.hana3d_mat
    query = {
        "asset_type": 'material',
    }

    build_query_common(query, props)

    return query


def mt(text):
    global search_start_time, prev_time
    alltime = time.time() - search_start_time
    since_last = time.time() - prev_time
    prev_time = time.time()
    utils.p(text, alltime, since_last)


def add_search_process(query, params):
    global search_threads

    while len(search_threads) > 0:
        old_thread = search_threads.pop(0)
        old_thread[0].stop()
        # TODO CARE HERE FOR ALSO KILLING THE THREADS...
        # AT LEAST NOW SEARCH DONE FIRST WON'T REWRITE AN OLDER ONE

    tempdir = paths.get_temp_dir('%s_search' % query['asset_type'])
    thread = Searcher(query, params)
    thread.start()

    search_threads.append([thread, tempdir, query['asset_type']])

    mt('thread started')


def search(get_next=False, author_id=''):
    ''' initialize searching'''
    global search_start_time

    search_start_time = time.time()
    # mt('start')
    scene = bpy.context.scene
    uiprops = scene.Hana3DUI

    if uiprops.asset_type == 'MODEL':
        if not hasattr(scene, 'hana3d'):
            return
        props = scene.hana3d_models
        query = build_query_model()

    if uiprops.asset_type == 'SCENE':
        if not hasattr(scene, 'hana3d_scene'):
            return
        props = scene.hana3d_scene
        query = build_query_scene()

    if uiprops.asset_type == 'MATERIAL':
        if not hasattr(scene, 'hana3d_mat'):
            return
        props = scene.hana3d_mat
        query = build_query_material()

    if props.is_searching and get_next:
        return

    if author_id != '':
        query['author_id'] = author_id

    if props.workspace != '' and not props.public_only:
        query['workspace'] = props.workspace

    # query['libraries'] = props.libraries

    tags = []
    for tag in props.tags_list.keys():
        if props.tags_list[tag].selected is True:
            tags.append(tag)
    query['tags'] = ','.join(tags)

    libraries = []
    for library in props.libraries_list.keys():
        if props.libraries_list[library].selected is True:
            libraries.append(library)
    query['libraries'] = ','.join(libraries)

    props.is_searching = True

    params = {'get_next': get_next}

    add_search_process(query, params)
    tasks_queue.add_task((ui.add_report, ('hana3d searching....', 2)))

    props.report = 'hana3d searching....'


class SearchOperator(Operator):
    """Tooltip"""

    bl_idname = "view3d.hana3d_search"
    bl_label = "hana3d asset search"
    bl_description = "Search online for assets"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}
    own: BoolProperty(name="own assets only", description="Find all own assets", default=False)

    author_id: StringProperty(
        name="Author ID",
        description="Author ID - search only assets by this author",
        default="",
        options={'SKIP_SAVE'},
    )

    get_next: BoolProperty(
        name="next page",
        description="get next page from previous search",
        default=False,
        options={'SKIP_SAVE'},
    )

    keywords: StringProperty(
        name="Keywords",
        description="Keywords",
        default="",
        options={'SKIP_SAVE'}
    )

    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        # TODO this should all get transferred to properties of the search operator,
        #  so sprops don't have to be fetched here at all.
        sprops = utils.get_search_props()
        if self.author_id != '':
            sprops.search_keywords = ''
        if self.keywords != '':
            sprops.search_keywords = self.keywords

        search(get_next=self.get_next, author_id=self.author_id)
        # bpy.ops.view3d.hana3d_asset_bar()

        return {'FINISHED'}


classes = [SearchOperator]


def register():
    bpy.app.handlers.load_post.append(scene_load)

    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.app.timers.register(timer_update)


def unregister():
    bpy.app.handlers.load_post.remove(scene_load)

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    if bpy.app.timers.is_registered(timer_update):
        bpy.app.timers.unregister(timer_update)
