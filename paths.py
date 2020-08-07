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

import os
import sys

import bpy

_presets = os.path.join(bpy.utils.user_resource('SCRIPTS'), "presets")
HANA3D_API = "/v1/"
HANA3D_AUTH_URL = "https://hana3d.us.auth0.com"
HANA3D_AUTH_CLIENT_ID_DEV = "K3Tp6c6bbvF8gT6nwK1buVZjpTeDeXfu"
HANA3D_AUTH_CLIENT_ID_PROD = "DDfs3mFwivtSoUOqwCZnJODaOhmwZvor"
HANA3D_AUTH_AUDIENCE_DEV = "https://staging-hana3d.com"
HANA3D_AUTH_AUDIENCE_PROD = "https://hana3d.com"
HANA3D_PLATFORM_URL_LOCAL = "https://staging.hana3d.com"
HANA3D_PLATFORM_URL_DEV = "https://staging.hana3d.com"
HANA3D_PLATFORM_URL_PROD = "https://hana3d.com"
HANA3D_AUTH_LANDING = "/landing"
HANA3D_SETTINGS_FILENAME = os.path.join(_presets, "hana3d.json")

RENDER_FARM_URL = 'https://api.notrenderfarm.com/dev'
RENDER_FARM_USER = 'users'
RENDER_FARM_UPLOAD = 'upload'
RENDER_FARM_PROJECT = 'projects'
RENDER_FARM_JOB = 'jobs'
RENDER_FARM_JOB_START = 'start'
RENDER_FARM_JOB_CANCEL = 'cancel'

URL_HANA3D_MAIN = 'https://api.hana3d.com'
URL_HANA3D_LOCAL = 'http://localhost:5000'
URL_HANA3D_DEV = os.getenv('URL_HANA3D_DEV', 'https://staging-api.hana3d.com')


def get_hana3d_url():
    if bpy.app.debug_value == 1:
        return URL_HANA3D_LOCAL

    if bpy.app.debug_value == 2:
        return URL_HANA3D_DEV

    return URL_HANA3D_MAIN


def find_in_local(text=''):
    fs = []
    for p, d, f in os.walk('.'):
        for file in f:
            if text in file:
                fs.append(file)
    return fs


def get_api_url():
    return get_hana3d_url() + HANA3D_API


def get_auth_url():
    return HANA3D_AUTH_URL


def get_platform_url():
    if bpy.app.debug_value == 1:
        return HANA3D_PLATFORM_URL_LOCAL

    if bpy.app.debug_value == 2:
        return HANA3D_PLATFORM_URL_DEV

    return HANA3D_PLATFORM_URL_PROD


def get_auth_landing_url():
    return get_platform_url() + HANA3D_AUTH_LANDING


def get_auth_client_id():
    if bpy.app.debug_value == 1:
        return HANA3D_AUTH_CLIENT_ID_DEV

    if bpy.app.debug_value == 2:
        return HANA3D_AUTH_CLIENT_ID_DEV

    return HANA3D_AUTH_CLIENT_ID_PROD


def get_auth_audience():
    if bpy.app.debug_value == 1:
        return HANA3D_AUTH_AUDIENCE_DEV

    if bpy.app.debug_value == 2:
        return HANA3D_AUTH_AUDIENCE_DEV

    return HANA3D_AUTH_AUDIENCE_PROD


def get_render_farm_user_url(email):
    return f'{RENDER_FARM_URL}/{RENDER_FARM_USER}/?email={email}'


def get_render_farm_upload_url():
    return f'{RENDER_FARM_URL}/{RENDER_FARM_UPLOAD}/?extension=.blend'


def get_render_farm_project_url(user_id):
    return f'{RENDER_FARM_URL}/{RENDER_FARM_USER}/{user_id}/{RENDER_FARM_PROJECT}'


def get_render_farm_job_url(project_id):
    return f'{RENDER_FARM_URL}/{RENDER_FARM_PROJECT}/{project_id}/{RENDER_FARM_JOB}'


def get_render_farm_job_start_url(job_id):
    return f'{RENDER_FARM_URL}/{RENDER_FARM_JOB}/{job_id}/{RENDER_FARM_JOB_START}'


def get_render_farm_job_get_url(user_id, job_id):
    return f'{RENDER_FARM_URL}/{RENDER_FARM_USER}/{user_id}/{RENDER_FARM_JOB}?id={job_id}'


def get_render_farm_job_cancel_url(job_id):
    return f'{RENDER_FARM_URL}/{RENDER_FARM_JOB}/{job_id}/{RENDER_FARM_JOB_CANCEL}'


def default_global_dict():
    from os.path import expanduser

    home = expanduser("~")
    return home + os.sep + 'hana3d_data'


def get_temp_dir(subdir=None):
    user_preferences = bpy.context.preferences.addons['hana3d'].preferences

    # tempdir = user_preferences.temp_dir
    tempdir = os.path.join(user_preferences.global_dir, 'temp')
    if tempdir.startswith('//'):
        tempdir = bpy.path.abspath(tempdir)
    try:
        if not os.path.exists(tempdir):
            os.makedirs(tempdir)
        if subdir is not None:
            tempdir = os.path.join(tempdir, subdir)
            if not os.path.exists(tempdir):
                os.makedirs(tempdir)
    except Exception:
        print('Cache directory not found. Resetting Cache folder path.')
        p = default_global_dict()
        if p == user_preferences.global_dir:
            print('Global dir was already default, please set a global directory in addon preferences to a dir where you have write permissions.')  # noqa E501
            return None
        user_preferences.global_dir = p
        tempdir = get_temp_dir(subdir=subdir)
    return tempdir


def get_download_dirs(asset_type):
    ''' get directories where assets will be downloaded'''
    subdmapping = {'model': 'models', 'scene': 'scenes', 'material': 'materials'}

    user_preferences = bpy.context.preferences.addons['hana3d'].preferences
    dirs = []
    if user_preferences.directory_behaviour == 'BOTH' or 'GLOBAL':
        ddir = user_preferences.global_dir
        if ddir.startswith('//'):
            ddir = bpy.path.abspath(ddir)
        if not os.path.exists(ddir):
            os.makedirs(ddir)

        subdirs = ['textures', 'models', 'scenes', 'materials']
        for subd in subdirs:
            subdir = os.path.join(ddir, subd)
            if not os.path.exists(subdir):
                os.makedirs(subdir)
            if subdmapping[asset_type] == subd:
                dirs.append(subdir)
    if (
        (
            user_preferences.directory_behaviour == 'BOTH'
            or user_preferences.directory_behaviour == 'LOCAL'
        )
        and bpy.data.is_saved
    ):
        # it's important local get's solved as second,
        # since for the linking process only last filename will be taken.
        #  For download process first name will be taken and if 2 filenames were returned,
        #  file will be copied to the 2nd path.
        ddir = user_preferences.project_subdir
        if ddir.startswith('//'):
            ddir = bpy.path.abspath(ddir)
            if not os.path.exists(ddir):
                os.makedirs(ddir)

        subdirs = ['textures', 'models', 'scenes', 'materials']
        for subd in subdirs:
            subdir = os.path.join(ddir, subd)
            if not os.path.exists(subdir):
                os.makedirs(subdir)
            if subdmapping[asset_type] == subd:
                dirs.append(subdir)

    return dirs


def slugify(slug):
    """
    Normalizes string, converts to lowercase, removes non-alpha characters,
    and converts spaces to hyphens.
    """
    import re

    slug = slug.lower()
    slug = slug.replace('.', '_')
    slug = slug.replace('"', '')
    slug = slug.replace(' ', '_')
    # import re
    # slug = unicodedata.normalize('NFKD', slug)
    # slug = slug.encode('ascii', 'ignore').lower()
    slug = re.sub(r'[^a-z0-9]+.- ', '-', slug).strip('-')
    slug = re.sub(r'[-]+', '-', slug)
    slug = re.sub(r'/', '_', slug)
    return slug


def extract_filename_from_url(url):
    if url is not None:
        imgname = url.split('/')[-1]
        imgname = imgname.split('?')[0]
        return imgname
    return ''


def get_download_filenames(asset_data):
    dirs = get_download_dirs(asset_data['asset_type'])
    file_names = []
    # fn = asset_data['file_name'].replace('blend_', '')
    if asset_data.get('download_url') is not None:
        # this means asset is already in scene and we don't need to check

        fn = extract_filename_from_url(asset_data['download_url'])
        for d in dirs:
            file_name = os.path.join(d, fn)
            file_names.append(file_name)
    return file_names


def delete_asset_debug(asset_data):
    from hana3d import download

    download.get_download_url(asset_data)

    file_names = get_download_filenames(asset_data)
    for f in file_names:
        if os.path.isfile(f):
            try:
                print(f)
                os.remove(f)
            except Exception:
                e = sys.exc_info()[0]
                print(e)
                pass


def get_clean_filepath():
    script_path = os.path.dirname(os.path.realpath(__file__))
    subpath = "blendfiles" + os.sep + "cleaned.blend"
    cp = os.path.join(script_path, subpath)
    return cp


def get_thumbnailer_filepath():
    script_path = os.path.dirname(os.path.realpath(__file__))
    # fpath = os.path.join(p, subpath)
    subpath = "blendfiles" + os.sep + "thumbnailer.blend"
    return os.path.join(script_path, subpath)


def get_material_thumbnailer_filepath():
    script_path = os.path.dirname(os.path.realpath(__file__))
    # fpath = os.path.join(p, subpath)
    subpath = "blendfiles" + os.sep + "material_thumbnailer_cycles.blend"
    return os.path.join(script_path, subpath)
    """
    for p in bpy.utils.script_paths():
        testfname= os.path.join(p, subpath)#p + '%saddons%sobject_fracture%sdata.blend' % (s,s,s)
        if os.path.isfile( testfname):
            fname=testfname
            return(fname)
    return None
    """


def get_addon_file(subpath=''):
    script_path = os.path.dirname(os.path.realpath(__file__))
    # fpath = os.path.join(p, subpath)
    return os.path.join(script_path, subpath)


def get_addon_thumbnail_path(name):
    script_path = os.path.dirname(os.path.realpath(__file__))
    # fpath = os.path.join(p, subpath)
    ext = name.split('.')[-1]
    next = ''
    if not (ext == 'jpg' or ext == 'png'):  # already has ext?
        next = '.jpg'
    subpath = "thumbnails" + os.sep + name + next
    return os.path.join(script_path, subpath)
