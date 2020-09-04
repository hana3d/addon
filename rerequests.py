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
    ui = reload(ui)
    utils = reload(utils)
else:
    from hana3d import hana3d_oauth, ui, utils

import bpy
import requests


def rerequest(method, url, **kwargs):
    # first get any additional args from kwargs
    immediate = False
    if kwargs.get('immediate'):
        immediate = kwargs['immediate']
        kwargs.pop('immediate')
    # first normal attempt
    response = requests.request(method, url, **kwargs)

    utils.p(method.upper(), url)
    utils.p(response.status_code)

    if not response.ok:
        ui.add_report(f'{method} request failed ({response.status_code}): {response.text}')
        try:
            code = response.json()['code']
        except Exception:
            code = None

        if response.status_code == 401 and code == 'token_expired':
            utils.p('refreshing token')
            ui.add_report('Refreshing token. If this fails, please login in Hana3D Login panel.', 10)  # noqa E501

            preferences = bpy.context.preferences.addons['hana3d'].preferences
            oauth_response = hana3d_oauth.refresh_token(
                preferences.api_key_refresh,
                immediate
            )
            updated_headers = utils.get_headers(api_key=oauth_response['access_token'])
            kwargs['headers'].update(updated_headers)
            response = requests.request(method, url, **kwargs)
    return response


def delete(url, **kwargs):
    response = rerequest('delete', url, **kwargs)
    return response


def get(url, **kwargs):
    response = rerequest('get', url, **kwargs)
    return response


def post(url, **kwargs):
    response = rerequest('post', url, **kwargs)
    return response


def put(url, **kwargs):
    response = rerequest('put', url, **kwargs)
    return response


def patch(url, **kwargs):
    response = rerequest('patch', url, **kwargs)
    return response
