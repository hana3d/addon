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

import queue

import bpy

from .config import HANA3D_NAME

state_update_queue = queue.Queue()


def threads_state_update():
    """Updates properties in main thread"""
    while not state_update_queue.empty():
        cmd = state_update_queue.get()
        try:
            exec(cmd)
            state_update_queue.task_done()
        except Exception as e:
            logging.error(f'Failed to execute command {cmd!r} ({e})')
    return 0.02


def get_global_name(asset_type, asset_name):
    if asset_type.upper() == 'MODEL':
        return f'bpy.data.objects["{asset_name}"]'
    if asset_type.upper() == 'MATERIAL':
        return f'bpy.data.materials["{asset_name}"]'
    if asset_type.upper() == 'SCENE':
        return f'bpy.data.scenes["{asset_name}"]'
    raise ValueError(f'Unexpected asset type {asset_type}')


def update_in_foreground(
        asset_type: str,
        asset_name: str,
        property_name: str,
        value,
        operation: str = '='):
    """Update blender objects in foreground to avoid threading errors"""
    global_object_name = get_global_name(asset_type, asset_name)
    cmd = f'{global_object_name}.{HANA3D_NAME}.{property_name} {operation} {value!r}'
    state_update_queue.put(cmd)


def update_state(
        asset_type: str,
        asset_name: str,
        property_name: str,
        value,
        operation: str = '='):
    global_name = get_global_name(asset_type, asset_name)
    update_in_foreground(global_name, property_name, value, operation)


def get_state(asset_type: str, asset_name: str, property_name: str):
    if asset_type.upper() == 'MODEL':
        asset = bpy.data.objects[asset_name]
    elif asset_type.upper() == 'MATERIAL':
        asset = bpy.data.materials[asset_name]
    elif asset_type.upper() == 'SCENE':
        asset = bpy.data.scenes[asset_name]
    else:
        raise ValueError(f'Unexpected asset type {asset_type}')
    asset_props = getattr(asset, HANA3D_NAME)
    return getattr(asset_props, property_name)


def register():
    bpy.app.timers.register(threads_state_update)


def unregister():
    bpy.app.timers.unregister(threads_state_update)
