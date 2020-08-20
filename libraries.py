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


from hana3d import utils


def library_items(context):
    profile = bpy.context.window_manager.get('hana3d profile')
    if profile is not None:
        user = profile.get('user')
        if user is not None:
            libraries = tuple(
                (library['id'], library['name'], '',) for library in user['libraries']
            )
            return libraries
    return ()


def update_libraries(context):
    return


class ListLibrariesOperator(bpy.types.Operator):
    """Libraries that the view will be assigned to.
If no library is selected the view will be assigned to the default library."""

    bl_idname = "object.hana3d_list_libraries"
    bl_label = "Hana3D List Libraries"
    bl_options = {'REGISTER', 'INTERNAL'}

    def draw(self, context):
        props = utils.get_upload_props()
        layout = self.layout
        # layout.prop(context.scene, 'hana3d_library_list')
        i = 0
        while hasattr(props, f'library_{i}'):
            layout.prop(props, f'library_{i}')
            i += 1

    def execute(self, context):
        return {'INTERFACE'}

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_popup(self)


class MockProps(bpy.types.PropertyGroup):
    test0: bpy.props.BoolProperty(
        name="Test0",
        description="Test0",
        default=False,
    )

    test1: bpy.props.BoolProperty(
        name="Test1",
        description="Test1",
        default=False,
    )

    test2: bpy.props.BoolProperty(
        name="Test2",
        description="Test2",
        default=False,
    )


def register():
    bpy.utils.register_class(ListLibrariesOperator)
    bpy.utils.register_class(MockProps)

    bpy.types.Scene.tests = bpy.props.PointerProperty(type=MockProps)


def unregister():
    del bpy.types.Scene.tests

    bpy.utils.unregister_class(MockProps)
    bpy.utils.unregister_class(ListLibrariesOperator)
