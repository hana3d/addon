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

import bpy
from bpy.props import StringProperty
from bpy.types import Operator

from . import paths, rerequests, utils
from .config import HANA3D_DESCRIPTION, HANA3D_NAME, HANA3D_PROFILE
from .report_tools import execute_wrapper
from .src.libraries.libraries import update_libraries_list
from .src.search import search
from .src.unified_props import Unified
from .src.upload import upload


def update_libraries(workspace):
    logging.debug('update_libraries')
    query = {
        'workspace_id': workspace
    }
    url = paths.get_api_url('libraries', query=query)
    headers = rerequests.get_headers()

    r = rerequests.get(url, headers=headers)
    assert r.ok, f'Failed to get library data: {r.text}'

    profile = bpy.context.window_manager[HANA3D_PROFILE]
    workspaces = profile['user']['workspaces']

    for k, v in enumerate(workspaces):
        if v['id'] == workspace:
            workspaces[k]['libraries'] = r.json()
            break

    profile['user']['workspaces'] = workspaces


class RemoveLibrarySearch(Operator):
    """Remove Library"""

    bl_idname = f"object.{HANA3D_NAME}_remove_library_search"
    bl_label = f"{HANA3D_DESCRIPTION} Remove Library"
    bl_options = {'REGISTER', 'INTERNAL'}

    library: StringProperty(name='Library', default='')

    @execute_wrapper
    def execute(self, context):
        search_props = search.get_search_props()
        search_props.libraries_list[self.library].selected = False
        return {'INTERFACE'}


class RemoveLibraryUpload(Operator):
    """Remove Library"""

    bl_idname = f"object.{HANA3D_NAME}_remove_library_upload"
    bl_label = f"{HANA3D_DESCRIPTION} Remove Library"
    bl_options = {'REGISTER', 'INTERNAL'}

    library: StringProperty(name='Library', default='')

    @execute_wrapper
    def execute(self, context):
        props = upload.get_upload_props()
        props.libraries_list[self.library].selected = False

        if 'view_props' in props.libraries_list[self.library].metadata:
            for view_prop in props.libraries_list[self.library].metadata['view_props']:
                name = f'{props.libraries_list[self.library].name} {view_prop["name"]}'
                if name in props.custom_props.keys():
                    del props.custom_props[name]
                    del props.custom_props_info[name]

        return {'INTERFACE'}


class RefreshLibraries(bpy.types.Operator):
    """Refresh Libraries"""

    bl_idname = f"object.{HANA3D_NAME}_refresh_libraries"
    bl_label = f"{HANA3D_DESCRIPTION} Refresh Libraries"
    bl_options = {'REGISTER', 'INTERNAL'}

    @execute_wrapper
    def execute(self, context):
        logging.debug('Refreshing libraries')
        unified_props = Unified(context).props

        search_props = search.get_search_props()
        update_libraries(unified_props.workspace)
        update_libraries_list(search_props, context)

        upload_props = upload.get_upload_props()
        update_libraries(unified_props.workspace)
        update_libraries_list(upload_props, context)

        utils.show_popup('Libraries updated!')
        return {'FINISHED'}


classes = (
    RemoveLibrarySearch,
    RemoveLibraryUpload,
    RefreshLibraries
)


def register():
    for c in classes:
        bpy.utils.register_class(c)


def unregister():
    for c in reversed(classes):
        bpy.utils.unregister_class(c)
