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

    utils = reload(utils)
else:
    from hana3d import utils

import bpy
from bpy.types import Operator


class ListLibrariesSearch(Operator):
    """Libraries that the view will be assigned to.
If no library is selected the view will be assigned to the default library."""

    bl_idname = "object.hana3d_list_libraries_search"
    bl_label = "Hana3D List Libraries"
    bl_options = {'REGISTER', 'INTERNAL'}

    def draw(self, context):
        props = utils.get_search_props()
        layout = self.layout
        for i in range(props.libraries_count):
            layout.prop(props, f'library_{i}')

    def execute(self, context):
        return {'INTERFACE'}

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_popup(self)


class ListLibrariesUpload(Operator):
    """Libraries that the view will be assigned to.
If no library is selected the view will be assigned to the default library."""

    bl_idname = "object.hana3d_list_libraries_upload"
    bl_label = "Hana3D List Libraries"
    bl_options = {'REGISTER', 'INTERNAL'}

    def draw(self, context):
        props = utils.get_upload_props()
        layout = self.layout
        for i in range(props.libraries_count):
            layout.prop(props, f'library_{i}')

    def execute(self, context):
        return {'INTERFACE'}

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_popup(self)


classes = (
    ListLibrariesSearch,
    ListLibrariesUpload
)


def register():
    for c in classes:
        bpy.utils.register_class(c)


def unregister():
    for c in reversed(classes):
        bpy.utils.unregister_class(c)
