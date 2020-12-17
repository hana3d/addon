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

from .config import HANA3D_DESCRIPTION, HANA3D_NAME
from .report_tools import execute_wrapper
from .src.upload import upload


class ShareAsset(bpy.types.Operator):
    """Share Asset ID"""

    bl_idname = f"object.{HANA3D_NAME}_share_asset"
    bl_label = f"{HANA3D_DESCRIPTION} Share Asset"
    bl_options = {'REGISTER', 'INTERNAL'}

    @execute_wrapper
    def execute(self, context):
        props = upload.get_upload_props()
        context.window_manager.clipboard = f"view_id:{props.view_id}"
        utils.show_popup('Copied to clipboard!')
        return {'FINISHED'}


classes = (
    ShareAsset,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
