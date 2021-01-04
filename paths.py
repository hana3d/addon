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
import logging
import os
import urllib.parse

import bpy

from .config import (
    HANA3D_AUTH_AUDIENCE,
    HANA3D_AUTH_CLIENT_ID,
    HANA3D_AUTH_LANDING,
    HANA3D_AUTH_URL,
    HANA3D_NAME,
    HANA3D_PLATFORM_URL,
    HANA3D_URL,
)
from .src.asset.asset_type import AssetType
from .src.search.query import Query

_presets = os.path.join(bpy.utils.user_resource('SCRIPTS'), 'presets')
HANA3D_SETTINGS_FILENAME = os.path.join(_presets, f'{HANA3D_NAME}.json')


def find_in_local(text=''):
    fs = []
    for p, d, f in os.walk('.'):
        for file in f:
            if text in file:
                fs.append(file)
    return fs


def get_api_url(*paths: str, query: dict = None) -> str:
    """Get API URL.

    Args:
        paths (str): path of the API url
        query (dict): Query passed as query string parameters. Defaults to None.

    Returns:
        str: the formatted API URL
    """
    base_url = f'{HANA3D_URL}/v1/'
    url = urllib.parse.urljoin(base_url, '/'.join(path.strip('/') for path in paths))
    if query is None:
        return url
    query_string = urllib.parse.urlencode(query)
    return f'{url}?{query_string}'



def get_auth_url():
    return HANA3D_AUTH_URL


def get_platform_url():
    return HANA3D_PLATFORM_URL


def get_auth_landing_url():
    return get_platform_url() + HANA3D_AUTH_LANDING


def get_auth_client_id():
    return HANA3D_AUTH_CLIENT_ID


def get_auth_audience():
    return HANA3D_AUTH_AUDIENCE


def default_global_dict():
    from os.path import expanduser

    home = expanduser('~')
    return home + os.sep + HANA3D_NAME + '_data'


def get_temp_dir(subdir=None):
    user_preferences = bpy.context.preferences.addons[HANA3D_NAME].preferences

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
        logging.error('Cache directory not found. Resetting Cache folder path.')
        p = default_global_dict()
        if p == user_preferences.global_dir:
            logging.error('Global dir was already default, please set a global directory in addon preferences to a dir where you have write permissions.')  # noqa E501
            return None
        user_preferences.global_dir = p
        tempdir = get_temp_dir(subdir=subdir)
    return tempdir


def get_download_dirs(asset_type):
    ''' get directories where assets will be downloaded'''
    subdmapping = {'model': 'models', 'scene': 'scenes', 'material': 'materials'}
    asset_type = asset_type.lower()

    user_preferences = bpy.context.preferences.addons[HANA3D_NAME].preferences
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
    if url is None:
        return ''
    path = urllib.parse.urlsplit(url).path

    return path.rpartition('/')[2]


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


def get_clean_filepath():
    script_path = os.path.dirname(os.path.realpath(__file__))
    subpath = f'blendfiles{os.sep}cleaned.blend'
    cp = os.path.join(script_path, subpath)
    return cp


def get_thumbnailer_filepath(asset_type: AssetType) -> str:
    """Get filepath for blend files used in thumbnailer.

    Parameters:
        asset_type: 'model' or 'material'

    Returns:
        str: filepath to blend file

    Raises:
        Exception: Invalid asset type for thumbnailer filepath
    """
    script_path = os.path.dirname(os.path.realpath(__file__))
    if asset_type == 'model':
        subpath = f'blendfiles{os.sep}thumbnailer.blend'
        return os.path.join(script_path, subpath)
    elif asset_type == 'material':
        subpath = f'blendfiles{os.sep}material_thumbnailer_cycles.blend'
        return os.path.join(script_path, subpath)
    raise Exception('Invalid asset type for thumbnailer filepath.')


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
    subpath = f'thumbnails{os.sep}{name}{next}'
    return os.path.join(script_path, subpath)
