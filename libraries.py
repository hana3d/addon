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

import bpy
from bpy.props import StringProperty
from bpy.types import Operator

from hana3d import utils, types
from hana3d.report_tools import execute_wrapper


class RemoveLibrarySearch(Operator):
    """Remove Library"""

    bl_idname = "object.hana3d_remove_library_search"
    bl_label = "Hana3D Remove Library"
    bl_options = {'REGISTER', 'INTERNAL'}

    library: StringProperty(name='Library', default='')

    @execute_wrapper
    def execute(self, context):
        props = utils.get_search_props()
        props.libraries_list[self.library].selected = False
        return {'INTERFACE'}


class RemoveLibraryUpload(Operator):
    """Remove Library"""

    bl_idname = "object.hana3d_remove_library_upload"
    bl_label = "Hana3D Remove Library"
    bl_options = {'REGISTER', 'INTERNAL'}

    library: StringProperty(name='Library', default='')

    @execute_wrapper
    def execute(self, context):
        props = utils.get_upload_props()
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

    bl_idname = "object.hana3d_refresh_libraries"
    bl_label = "Hana3D Refresh Libraries"
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        utils.update_libraries(utils.get_search_props().workspace)
        types.update_libraries_list(utils.get_search_props(), context)
        utils.update_libraries(utils.get_upload_props().workspace)
        types.update_libraries_list(utils.get_upload_props(), context)
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
