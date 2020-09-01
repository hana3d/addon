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
    tasks_queue = reload(tasks_queue)
    ui = reload(ui)
    utils = reload(utils)
else:
    from hana3d import hana3d_oauth, paths, tasks_queue, ui, utils

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

    utils.p(url)
    utils.p(response.status_code)

    if response.status_code == 401:
        try:
            rdata = response.json()
        except Exception:
            rdata = {}

        tasks_queue.add_task(
            (ui.add_report, (method + ' request Failed.' + str(rdata.get('detail')),))
        )

        if rdata.get('code') == 'token_expired':
            user_preferences = bpy.context.preferences.addons['hana3d'].preferences
            if user_preferences.api_key != '':
                if user_preferences.api_key_refresh != '':
                    tasks_queue.add_task(
                        (ui.add_report, ('refreshing token. If this fails, please login in Hana3D Login panel.', 10,),)  # noqa E501
                    )
                    refresh_url = paths.get_hana3d_url()
                    auth_token, refresh_token, oauth_response = hana3d_oauth.refresh_token(
                        user_preferences.api_key_refresh,
                        refresh_url
                    )

                    # utils.p(auth_token, refresh_token)
                    if auth_token is not None:
                        if immediate:
                            # this can write tokens occasionally into prefs.
                            # used e.g. in upload. Only possible in non-threaded tasks
                            bpy.context.preferences.addons[
                                'hana3d'
                            ].preferences.api_key = auth_token
                            bpy.context.preferences.addons[
                                'hana3d'
                            ].preferences.api_key_refresh = refresh_token

                        kwargs['headers'].update(utils.get_headers())
                        response = requests.request(method, url, **kwargs)
                        utils.p('reresult', response.status_code)
                        if response.status_code >= 400:
                            utils.p('reresult', response.text)
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
