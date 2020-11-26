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
import datetime
import functools
import getpass
import traceback
import uuid

import addon_utils
import bpy
import requests

from . import paths
from .config import HANA3D_DESCRIPTION


def get_addon_version():
    for addon in addon_utils.modules():
        if addon.bl_info['name'] == HANA3D_DESCRIPTION:
            return str(addon.bl_info['version'])


def format_exception(exc: Exception) -> dict:
    if len(exc.args) == 1 and isinstance(exc.args[0], dict):
        error_msg = exc.args[0]
    else:
        error_msg = ';'.join(str(arg) for arg in exc.args)
    return {
        'errorMessage': error_msg,
        'errorType': exc.__class__.__name__,
        'stackTrace': traceback.format_exc()
    }


def execute_wrapper(func):
    """Decorator to build error reports"""
    @functools.wraps(func)
    def wrapper(event, context):
        try:
            return func(event, context)
        except Exception as e:
            data = {
                'event_id': str(uuid.uuid4()),
                'addon_version': get_addon_version(),
                'blender_version': bpy.app.version_string,
                'timestamp': datetime.datetime.now().isoformat(),
                'user': getpass.getuser(),
                'error': format_exception(e)
            }
            url = paths.get_api_url('report')
            requests.post(url, json=data)
            raise

    return wrapper
