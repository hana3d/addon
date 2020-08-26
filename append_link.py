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


if "bpy" in locals():
    from importlib import reload

    utils = reload(utils)
    render_settings = reload(render_settings)
else:
    from hana3d import utils, render_settings

import bpy


def append_material(file_name, matname=None, link=False, fake_user=True):
    '''append a material type asset'''
    # first, we have to check if there is a material with same name
    # in previous step there's check if the imported material
    # is already in the scene, so we know same name != same material

    mats_before = bpy.data.materials.keys()

    with bpy.data.libraries.load(file_name, link=link, relative=True) as (data_from, data_to):
        for m in data_from.materials:
            if m == matname or matname is None:
                data_to.materials = [m]
                # print(m, type(m))
                matname = m
                break

    # we have to find the new material :(
    for mname in bpy.data.materials.keys():
        if mname not in mats_before:
            mat = bpy.data.materials[mname]
            break

    if fake_user:
        mat.use_fake_user = True

    return mat


def copy_scene_render_attributes(from_scene, to_scene, settings):
    for attribute in settings:
        from_attribute = getattr(from_scene, attribute)
        to_attribute = getattr(to_scene, attribute)
        for setting in settings[attribute]:
            value = getattr(from_attribute, setting)
            setattr(to_attribute, setting, value)


def copy_curves(from_scene: bpy.types.Scene, to_scene: bpy.types.Scene):
    for curve in to_scene.view_settings.curve_mapping.curves:
        while len(curve.points) > 2:
            curve.points.remove(curve.points[-1])
        curve.points[0].location = (0, 0)
        curve.points[1].location = (1, 1)

    for i, curve in enumerate(from_scene.view_settings.curve_mapping.curves):
        points = to_scene.view_settings.curve_mapping.curves[i].points
        while len(points) < len(curve.points):
            points.new(0, 0)
        for j, point in enumerate(curve.points):
            points[j].location = point.location

    to_scene.view_settings.curve_mapping.black_level = (
        from_scene.view_settings.curve_mapping.black_level
    )
    to_scene.view_settings.curve_mapping.white_level = (
        from_scene.view_settings.curve_mapping.white_level
    )
    to_scene.view_settings.curve_mapping.update()


def copy_attributes(attributes, old_prop, new_prop):
    """copies the list of attributes from the old to the new prop if the attribute exists"""

    for attr in attributes:
        if hasattr(new_prop, attr):
            setattr(new_prop, attr, getattr(old_prop, attr))


def get_node_attributes(node):
    """returns a list of all propertie identifiers if they shoulnd't be ignored"""

    ignore_attributes = ("rna_type", "type", "dimensions", "inputs",
                         "outputs", "internal_links", "select")

    attributes = []
    for attr in node.bl_rna.properties:
        if attr.identifier not in ignore_attributes and not attr.identifier.split("_")[0] == "bl":
            attributes.append(attr.identifier)

    return attributes


def copy_nodes(nodes, group):
    """copies all nodes from the given list into the group with their attributes"""

    input_attributes = ("default_value", "name")
    output_attributes = ("default_value", "name")

    for node in nodes:
        new_node = group.nodes.new(node.bl_idname)
        node_attributes = get_node_attributes(node)
        copy_attributes(node_attributes, node, new_node)

        for i, inp in enumerate(node.inputs):
            copy_attributes(input_attributes, inp, new_node.inputs[i])

        for i, out in enumerate(node.outputs):
            copy_attributes(output_attributes, out, new_node.outputs[i])


def copy_links(context, nodes, group):
    """copies all links between the nodes in the list to the nodes in the group"""

    for node in nodes:
        new_node = group.nodes[node.name]

        for i, inp in enumerate(node.inputs):
            for link in inp.links:
                connected_node = group.nodes[link.from_node.name]
                group.links.new(connected_node.outputs[link.from_socket.name], new_node.inputs[i])


def append_scene(file_name, scenename=None, link=False, fake_user=False):
    '''append a scene type asset'''
    context = bpy.context
    scene = context.scene
    props = scene.hana3d_scene

    if props.merge_add == 'MERGE' and scenename is None:
        with bpy.data.libraries.load(file_name, link=link, relative=True) as (data_from, data_to):
            data_to.collections = [name for name in data_from.collections]
            scene_name = data_from.scenes[0]
            data_to.scenes = [scene_name]

        imported_scene = data_to.scenes[0]
        scene_collection = bpy.data.collections.new(scene_name)
        scene.collection.children.link(scene_collection)
        for col in data_to.collections:
            scene_collection.children.link(col)
        scene.camera = imported_scene.camera
        if props.import_world:
            scene.world = imported_scene.world

        if props.import_render:
            copy_scene_render_attributes(imported_scene, scene, render_settings.SETTINGS)
            if scene.view_settings.use_curve_mapping:
                copy_curves(imported_scene, scene)

        if props.import_compositing:
            scene.use_nodes = True

            for node in scene.node_tree.nodes:
                scene.node_tree.nodes.clear()
            nodes = imported_scene.node_tree.nodes
            group = scene.node_tree
            copy_nodes(nodes, group)
            copy_links(context, nodes, group)

        window = context.window_manager.windows[0]
        ctx = {'window': window, 'screen': window.screen, 'scene': imported_scene}
        bpy.ops.scene.hana3d_delete_scene(ctx)

        return scene

    with bpy.data.libraries.load(file_name, link=link, relative=True) as (data_from, data_to):
        for s in data_from.scenes:
            if s == scenename or scenename is None:
                data_to.scenes = [s]
                scenename = s
    scene = bpy.data.scenes[scenename]
    if fake_user:
        scene.use_fake_user = True
    return scene


def link_collection(file_name, obnames=[], location=(0, 0, 0), link=False, parent=None, **kwargs):
    '''link an instanced group - model type asset'''
    sel = utils.selection_get()

    with bpy.data.libraries.load(file_name, link=link, relative=True) as (data_from, data_to):
        for col in data_from.collections:
            print('linking this ', col)
            if col == kwargs['name']:
                data_to.collections = [col]

    rotation = (0, 0, 0)
    if kwargs.get('rotation') is not None:
        rotation = kwargs['rotation']

    bpy.ops.object.empty_add(type='PLAIN_AXES', location=location, rotation=rotation)
    main_object = bpy.context.view_layer.objects.active
    main_object.instance_type = 'COLLECTION'

    main_object.parent = parent
    main_object.matrix_world.translation = location

    for col in bpy.data.collections:
        if col.library is not None:
            fp = bpy.path.abspath(col.library.filepath)
            fp1 = bpy.path.abspath(file_name)
            if fp == fp1:
                main_object.instance_collection = col
                break

    main_object.name = main_object.instance_collection.name

    # bpy.ops.wm.link(
    #     directory=file_name + "/Collection/",
    #     filename=kwargs['name'],
    #     link=link,
    #     instance_collections=True,
    #     autoselect=True
    # )
    # main_object = bpy.context.view_layer.objects.active
    # if kwargs.get('rotation') is not None:
    #     main_object.rotation_euler = kwargs['rotation']
    # main_object.location = location

    utils.selection_set(sel)
    return main_object, []


def append_objects(file_name, obnames=[], location=(0, 0, 0), link=False, **kwargs):
    '''append objects into scene individually'''

    with bpy.data.libraries.load(file_name, link=link, relative=True) as (data_from, data_to):
        sobs = []
        for ob in data_from.objects:
            if ob in obnames or obnames == []:
                sobs.append(ob)
        data_to.objects = sobs

    sel = utils.selection_get()
    bpy.ops.object.select_all(action='DESELECT')

    return_obs = []
    main_object = None
    hidden_objects = []

    for obj in data_to.objects:
        if obj is not None:
            if obj in bpy.context.view_layer.active_layer_collection.collection.objects.values():
                bpy.context.view_layer.active_layer_collection.collection.objects.unlink(obj)
            bpy.context.view_layer.active_layer_collection.collection.objects.link(obj)
            if obj.parent is None:
                obj.location = location
                main_object = obj
            obj.select_set(True)
            if link is True:
                if obj.hide_viewport:
                    hidden_objects.append(obj)
                    obj.hide_viewport = False
            return_obs.append(obj)
    if link is True:
        bpy.ops.object.make_local(type='SELECT_OBJECT')
        for ob in hidden_objects:
            ob.hide_viewport = True

    if kwargs.get('rotation') is not None:
        main_object.rotation_euler = kwargs['rotation']

    if kwargs.get('parent') is not None:
        main_object.parent = bpy.data.objects[kwargs['parent']]
        main_object.matrix_world.translation = location

    bpy.ops.object.select_all(action='DESELECT')

    utils.selection_set(sel)

    return main_object, return_obs


class DeleteSceneWorkaround(bpy.types.Operator):
    bl_idname = "scene.hana3d_delete_scene"
    bl_label = "Test Operator"

    def execute(self, context):
        bpy.data.scenes.remove(context.scene, do_unlink=True)
        return {'FINISHED'}


def register():
    bpy.utils.register_class(DeleteSceneWorkaround)


def unregister():
    bpy.utils.unregister_class(DeleteSceneWorkaround)
