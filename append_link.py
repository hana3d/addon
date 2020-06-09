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
    ui = reload(ui)
    render_settings = reload(render_settings)
else:
    from asset_manager_real2u import utils, ui, render_settings

import bpy
import uuid


def append_brush(file_name, brushname=None, link=False, fake_user=True):
    '''append a brush'''
    with bpy.data.libraries.load(file_name, link=link, relative=True) as (data_from, data_to):
        for m in data_from.brushes:
            if m == brushname or brushname is None:
                data_to.brushes = [m]
                brushname = m
    brush = bpy.data.brushes[brushname]
    if fake_user:
        brush.use_fake_user = True
    return brush


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
                break;

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

    to_scene.view_settings.curve_mapping.black_level = from_scene.view_settings.curve_mapping.black_level
    to_scene.view_settings.curve_mapping.white_level = from_scene.view_settings.curve_mapping.white_level
    to_scene.view_settings.curve_mapping.update()


def append_scene(file_name, scenename=None, link=False, fake_user=False):
    '''append a scene type asset'''
    scene = bpy.context.scene
    props = scene.asset_manager_real2u_scene

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

        imported_scene.user_clear()
        bpy.data.scenes.remove(imported_scene, do_unlink=False)

        return scene

    with bpy.data.libraries.load(file_name, link=link, relative=True) as (data_from, data_to):
        for s in data_from.scenes:
            if s == scenename or scenename is None:
                data_to.scenes = [s]
                scenename = s
    scene = bpy.data.scenes[scenename]
    if fake_user:
        scene.use_fake_user = True
    # scene has to have a new uuid, so user reports aren't screwed.
    scene['uuid'] = str(uuid.uuid4())
    return scene


def link_collection(file_name, obnames=[], location=(0, 0, 0), link=False, parent = None, **kwargs):
    '''link an instanced group - model type asset'''
    sel = utils.selection_get()

    with bpy.data.libraries.load(file_name, link=link, relative=True) as (data_from, data_to):
        scols = []
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

    # bpy.ops.wm.link(directory=file_name + "/Collection/", filename=kwargs['name'], link=link, instance_collections=True,
    #                 autoselect=True)
    # main_object = bpy.context.view_layer.objects.active
    # if kwargs.get('rotation') is not None:
    #     main_object.rotation_euler = kwargs['rotation']
    # main_object.location = location

    utils.selection_set(sel)
    return main_object, []


def append_particle_system(file_name, obnames=[], location=(0, 0, 0), link=False, **kwargs):
    '''link an instanced group - model type asset'''

    pss = []
    with bpy.data.libraries.load(file_name, link=link, relative=True) as (data_from, data_to):
        for ps in data_from.particles:
            pss.append(ps)
        data_to.particles = pss

    s = bpy.context.scene
    sel = utils.selection_get()

    target_object = bpy.context.scene.objects.get(kwargs['target_object'])
    if target_object is not None and target_object.type == 'MESH':
        target_object.select_set(True)
        bpy.context.view_layer.objects.active = target_object

        for ps in pss:
            # now let's tune this ps to the particular objects area:
            totarea = 0
            for p in target_object.data.polygons:
                totarea += p.area
            count = int(ps.count * totarea)
            if ps.child_type in ('INTERPOLATED', 'SIMPLE'):
                total_count = count * ps.rendered_child_count
                disp_count = count * ps.child_nbr
            else:
                total_count = count
            threshold = 2000
            total_max_threshold = 50000
            # emitting too many parent particles just kills blender now:
            if count > total_max_threshold:
                ratio = round(count / total_max_threshold)

                if ps.child_type in ('INTERPOLATED', 'SIMPLE'):
                    ps.rendered_child_count *= ratio
                else:
                    ps.child_type = 'INTERPOLATED'
                    ps.rendered_child_count = ratio
                count = max(2, int(count / ratio))
            ps.display_percentage = min(ps.display_percentage, max(1, int(100 * threshold / total_count)))

            ps.count = count
            bpy.ops.object.particle_system_add()
            target_object.particle_systems[-1].settings = ps

        target_object.select_set(False)
    utils.selection_set(sel)
    return target_object, []


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
