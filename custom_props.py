import bpy


class BlenderkitCustomProps(bpy.types.PropertyGroup):
    key: bpy.props.StringProperty(
        name="Key",
        description="Name of new property",
        default='author'
    )

    value: bpy.props.StringProperty(
        name="Value",
        description="Value of new property",
        default='Real2U'
    )


class ModelCreateCustomProps(bpy.types.Operator):
    """Model Create Custom Props"""
    bl_idname = "blenderkit.model_custom_props"
    bl_label = "Model Custom Props"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        obj = context.active_object

        key = scene.blenderkit_custom_props.key
        value = scene.blenderkit_custom_props.value

        obj.blenderkit.custom_props[key] = value
        return {'FINISHED'}


class MaterialCreateCustomProps(bpy.types.Operator):
    """Material Create Custom Props"""
    bl_idname = "blenderkit.material_custom_props"
    bl_label = "Material Custom Props"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        mat = context.active_object.active_material

        key = scene.blenderkit_custom_props.key
        value = scene.blenderkit_custom_props.value

        mat.blenderkit.custom_props[key] = value
        return {'FINISHED'}


class CustomPropsPropertyGroup(bpy.types.PropertyGroup):
    props_number: bpy.props.IntProperty()


classes = (
    BlenderkitCustomProps,
    ModelCreateCustomProps,
    MaterialCreateCustomProps,
    CustomPropsPropertyGroup
)


def register_custom_props():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Scene.blenderkit_custom_props = bpy.props.PointerProperty(type=BlenderkitCustomProps)


def unregister_custom_props():
    del bpy.types.Scene.blenderkit_custom_props

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
