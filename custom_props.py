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


class Hana3DCustomProps(bpy.types.PropertyGroup):
    key: bpy.props.StringProperty(name="Key", description="Name of new property", default='author')

    value: bpy.props.StringProperty(
        name="Value",
        description="Value of new property",
        default='Real2U'
    )


class ModelCreateCustomProps(bpy.types.Operator):
    """Model Create Custom Props"""

    bl_idname = "hana3d.model_custom_props"
    bl_label = "Model Custom Props"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        obj = context.active_object

        key = scene.hana3d_custom_props.key
        value = scene.hana3d_custom_props.value

        obj.hana3d.custom_props[key] = value
        return {'FINISHED'}


class MaterialCreateCustomProps(bpy.types.Operator):
    """Material Create Custom Props"""

    bl_idname = "hana3d.material_custom_props"
    bl_label = "Material Custom Props"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        mat = context.active_object.active_material

        key = scene.hana3d_custom_props.key
        value = scene.hana3d_custom_props.value

        mat.hana3d.custom_props[key] = value
        return {'FINISHED'}


class CustomPropsPropertyGroup(bpy.types.PropertyGroup):
    props_number: bpy.props.IntProperty()


classes = (
    Hana3DCustomProps,
    ModelCreateCustomProps,
    MaterialCreateCustomProps,
    CustomPropsPropertyGroup,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Scene.hana3d_custom_props = bpy.props.PointerProperty(type=Hana3DCustomProps)


def unregister():
    del bpy.types.Scene.hana3d_custom_props

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
