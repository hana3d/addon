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

    paths = reload(paths)
    version_checker = reload(version_checker)
else:
    from hana3d import paths, version_checker

import json
import os
import sys
import uuid
from typing import List, Tuple

import bpy
from mathutils import Vector

ABOVE_NORMAL_PRIORITY_CLASS = 0x00008000
BELOW_NORMAL_PRIORITY_CLASS = 0x00004000
HIGH_PRIORITY_CLASS = 0x00000080
IDLE_PRIORITY_CLASS = 0x00000040
NORMAL_PRIORITY_CLASS = 0x00000020
REALTIME_PRIORITY_CLASS = 0x00000100


def get_process_flags():
    flags = BELOW_NORMAL_PRIORITY_CLASS
    if sys.platform != 'win32':  # TODO test this on windows
        flags = 0
    return flags


def activate(ob):
    bpy.ops.object.select_all(action='DESELECT')
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob


def selection_get():
    aob = bpy.context.view_layer.objects.active
    selobs = bpy.context.view_layer.objects.selected[:]
    return (aob, selobs)


def selection_set(sel):
    bpy.ops.object.select_all(action='DESELECT')
    bpy.context.view_layer.objects.active = sel[0]
    for ob in sel[1]:
        ob.select_set(True)


def get_active_model():
    if bpy.context.view_layer.objects.active is not None:
        ob = bpy.context.view_layer.objects.active
        while ob.parent is not None:
            ob = ob.parent
        return ob
    return None


def get_selected_models():
    obs = bpy.context.selected_objects[:]
    done = {}
    parents = []
    for ob in obs:
        if ob not in done:
            while (
                ob.parent is not None
                and ob not in done
                and ob.hana3d.view_id != ''
                and ob.instance_collection is not None
            ):
                done[ob] = True
                ob = ob.parent

            if ob not in parents and ob not in done:
                if ob.hana3d.name != '' or ob.instance_collection is not None:
                    parents.append(ob)
            done[ob] = True

    # if no hana3d - like objects were found, use the original selection.
    if len(parents) == 0:
        parents = obs
    return parents


def get_search_props():
    scene = bpy.context.scene
    if scene is None:
        return
    uiprops = scene.Hana3DUI
    props = None
    if uiprops.asset_type == 'MODEL':
        if not hasattr(scene, 'hana3d_models'):
            return
        props = scene.hana3d_models
    if uiprops.asset_type == 'SCENE':
        if not hasattr(scene, 'hana3d_scene'):
            return
        props = scene.hana3d_scene
    if uiprops.asset_type == 'MATERIAL':
        if not hasattr(scene, 'hana3d_mat'):
            return
        props = scene.hana3d_mat
    return props


def get_active_asset():
    scene = bpy.context.scene
    ui_props = scene.Hana3DUI
    if ui_props.asset_type == 'MODEL':
        if bpy.context.view_layer.objects.active is not None:
            ob = get_active_model()
            return ob
    if ui_props.asset_type == 'SCENE':
        return bpy.context.scene

    elif ui_props.asset_type == 'MATERIAL':
        if (
            bpy.context.view_layer.objects.active is not None
            and bpy.context.active_object.active_material is not None
        ):
            return bpy.context.active_object.active_material
    return None


def get_upload_props():
    active_asset = get_active_asset()
    if active_asset is None:
        return None
    return active_asset.hana3d


def get_app_version():
    ver = bpy.app.version
    return '%i.%i.%i' % (ver[0], ver[1], ver[2])


def add_version(data):
    app_version = get_app_version()
    addon_version = version_checker.get_addon_version()
    data["sourceAppName"] = "blender"
    data["sourceAppVersion"] = app_version
    data["addonVersion"] = addon_version


def comma2array(text):
    commasep = text.split(',')
    ar = []
    for i, s in enumerate(commasep):
        s = s.strip()
        if s != '':
            ar.append(s)
    return ar


def get_export_data(
        asset_type: str,
        path_computing: str = 'uploading',
        path_state: str = 'upload_state'):
    export_data = {
        "type": asset_type,
    }
    upload_params = {}
    if asset_type == 'MODEL':
        # Prepare to save the file
        mainmodel = get_active_model()

        props = mainmodel.hana3d

        obs = get_hierarchy(mainmodel)
        obnames = []
        for ob in obs:
            obnames.append(ob.name)
        export_data["models"] = obnames
        export_data["thumbnail_path"] = bpy.path.abspath(props.thumbnail)

        eval_path = f"bpy.data.objects['{mainmodel.name}']"

        upload_data = {
            "assetType": 'model',
        }
        upload_params = {
            "dimensionX": round(props.dimensions[0], 4),
            "dimensionY": round(props.dimensions[1], 4),
            "dimensionZ": round(props.dimensions[2], 4),
            "boundBoxMinX": round(props.bbox_min[0], 4),
            "boundBoxMinY": round(props.bbox_min[1], 4),
            "boundBoxMinZ": round(props.bbox_min[2], 4),
            "boundBoxMaxX": round(props.bbox_max[0], 4),
            "boundBoxMaxY": round(props.bbox_max[1], 4),
            "boundBoxMaxZ": round(props.bbox_max[2], 4),
            "faceCount": props.face_count,
            "faceCountRender": props.face_count_render,
            "objectCount": props.object_count,
            "manufacturer": props.manufacturer,
            "designer": props.designer,
        }

    elif asset_type == 'SCENE':
        # Prepare to save the file
        s = bpy.context.scene

        props = s.hana3d

        export_data["scene"] = s.name
        export_data["thumbnail_path"] = bpy.path.abspath(props.thumbnail)

        eval_path = f"bpy.data.scenes['{s.name}']"

        upload_data = {
            "assetType": 'scene',
        }
        upload_params = {
            # TODO add values
            # "faceCount": 1,  # props.face_count,
            # "faceCountRender": 1,  # props.face_count_render,
            # "objectCount": 1,  # props.object_count,
        }

    elif asset_type == 'MATERIAL':
        mat = bpy.context.active_object.active_material
        props = mat.hana3d

        # props.name = mat.name

        export_data["material"] = str(mat.name)
        export_data["thumbnail_path"] = bpy.path.abspath(props.thumbnail)

        eval_path = f"bpy.data.materials['{mat.name}']"

        upload_data = {
            "assetType": 'material',
        }

        upload_params = {}
    else:
        raise Exception(f'Unexpected asset_type={asset_type}')

    bg_process_params = {
        'eval_path_computing': f'{eval_path}.hana3d.{path_computing}',
        'eval_path_state': f'{eval_path}.hana3d.{path_state}',
        'eval_path': eval_path,
    }

    add_version(upload_data)

    upload_data["name"] = props.name
    upload_data["description"] = props.description
    upload_data["tags"] = comma2array(props.tags)

    upload_data['parameters'] = upload_params

    upload_data["is_public"] = props.is_public
    if props.workspace != '' and not props.is_public:
        upload_data['workspace'] = props.workspace

    metadata = {}
    if hasattr(props, 'custom_props'):
        metadata.update(props.custom_props)
    if metadata:
        upload_data['metadata'] = metadata

    upload_data['libraries'] = []
    if props.libraries == '':
        upload_data['libraries'].append({
            'id': props.default_library
        })
    else:
        libraries = comma2array(props.libraries)
        for library_id in libraries:
            library = {}
            library.update({
                'id': library_id
            })
            if props.custom_props.keys() != []:
                custom_props = {}
                for name in props.custom_props.keys():
                    value = props.custom_props[name]
                    key = props.custom_props_info[name]['key']
                    prop_library_id = props.custom_props_info[name]['library_id']
                    if prop_library_id == library_id:
                        custom_props.update({key: value})
                library.update({'metadata': {'view_props': custom_props}})
            upload_data['libraries'].append(library)

    export_data['publish_message'] = props.publish_message

    return export_data, upload_data, bg_process_params, props


def previmg_name(index, fullsize=False):
    if not fullsize:
        return '.hana3d_preview_' + str(index).zfill(2)
    else:
        return '.hana3d_preview_full_' + str(index).zfill(2)


def load_prefs():
    user_preferences = bpy.context.preferences.addons['hana3d'].preferences
    # if user_preferences.api_key == '':
    fpath = paths.HANA3D_SETTINGS_FILENAME
    if os.path.exists(fpath):
        with open(fpath, 'r') as s:
            prefs = json.load(s)
            user_preferences.api_key = prefs.get('API_key', '')
            user_preferences.global_dir = prefs.get('global_dir', paths.default_global_dict())
            user_preferences.api_key_refresh = prefs.get('API_key_refresh', '')
            user_preferences.api_key_life = prefs.get('API_key_life', 3600)
            user_preferences.api_key_timeout = prefs.get('API_key_timeout', 0)
            user_preferences.id_token = prefs.get('ID_Token', '')


def save_prefs(self, context):
    # first check context, so we don't do this on registration or blender startup
    if not bpy.app.background:  # (hasattr kills blender)
        user_preferences = bpy.context.preferences.addons['hana3d'].preferences
        # we test the api key for length, so not a random accidentally typed sequence gets saved.
        lk = len(user_preferences.api_key)
        if 0 < lk < 25:
            # reset the api key in case the user writes some nonsense,
            # e.g. a search string instead of the Key
            user_preferences.api_key = ''
            props = get_search_props()
            props.report = 'Login failed. Please paste a correct API Key.'

        prefs = {
            'API_key': user_preferences.api_key,
            'API_key_refresh': user_preferences.api_key_refresh,
            'global_dir': user_preferences.global_dir,
            'API_key_life': user_preferences.api_key_life,
            'API_key_timeout': user_preferences.api_key_timeout,
            'ID_Token': user_preferences.id_token,
        }
        try:
            fpath = paths.HANA3D_SETTINGS_FILENAME
            if not os.path.exists(paths._presets):
                os.makedirs(paths._presets)
            with open(fpath, 'w') as s:
                json.dump(prefs, s)
        except Exception as e:
            print(e)


def get_hidden_image(
        thumbnail_path: str,
        image_name: str,
        force_reload: bool = False,
        default_image: str = 'thumbnail_notready.jpg'):
    if thumbnail_path.startswith('//'):
        thumbnail_path = bpy.path.abspath(thumbnail_path)
    if not os.path.exists(thumbnail_path) or thumbnail_path == '':
        thumbnail_path = paths.get_addon_thumbnail_path(default_image)

    hidden_name = f'.{image_name}'
    img = bpy.data.images.get(hidden_name)

    if img is None:
        img = bpy.data.images.load(thumbnail_path)
        img.name = hidden_name
        img.colorspace_settings.name = 'Linear'
    if img.filepath != thumbnail_path or force_reload:
        if img.packed_file is not None:
            img.unpack(method='USE_ORIGINAL')

        img.filepath = thumbnail_path
        img.reload()
    return img


def get_thumbnail(name):
    p = paths.get_addon_thumbnail_path(name)
    name = '.%s' % name
    img = bpy.data.images.get(name)
    if img is None:
        img = bpy.data.images.load(p)
        img.colorspace_settings.name = 'Linear'
        img.name = name
        img.name = name

    return img


def p(text, text1='', text2='', text3='', text4='', text5=''):
    '''debug printing depending on blender's debug value'''
    if os.getenv('HANA3D_ENV') in ('local', 'dev'):
        print(text, text1, text2, text3, text4, text5)


def pprint(data):
    '''pretty print jsons'''
    p(json.dumps(data, indent=4, sort_keys=True))


def get_hierarchy(ob):
    '''get all objects in a tree'''
    obs = []
    doobs = [ob]
    while len(doobs) > 0:
        o = doobs.pop()
        doobs.extend(o.children)
        obs.append(o)
    return obs


def select_hierarchy(ob, state=True):
    obs = get_hierarchy(ob)
    for ob in obs:
        ob.select_set(state)
    return obs


def delete_hierarchy(ob):
    obs = get_hierarchy(ob)
    bpy.ops.object.delete({"selected_objects": obs})


def get_bounds_snappable(obs, use_modifiers=False):
    # progress('getting bounds of object(s)')
    parent = obs[0]
    while parent.parent is not None:
        parent = parent.parent
    maxx = maxy = maxz = -10000000
    minx = miny = minz = 10000000

    obcount = 0  # calculates the mesh obs. Good for non-mesh objects
    matrix_parent = parent.matrix_world
    for ob in obs:
        # bb=ob.bound_box
        mw = ob.matrix_world
        # while parent.parent is not None:
        #     mw =

        if ob.type == 'MESH' or ob.type == 'CURVE':
            # If to_mesh() works we can use it on curves and any other ob type almost.
            # disabled to_mesh for 2.8 by now, not wanting to use dependency graph yet.
            depsgraph = bpy.context.evaluated_depsgraph_get()

            object_eval = ob.evaluated_get(depsgraph)
            if ob.type == 'CURVE':
                mesh = object_eval.to_mesh()
            else:
                mesh = object_eval.data

            # to_mesh(context.depsgraph, apply_modifiers=self.applyModifiers, calc_undeformed=False)
            obcount += 1
            if mesh is not None:
                for c in mesh.vertices:
                    coord = c.co
                    parent_coord = (
                        matrix_parent.inverted() @ mw @ Vector((coord[0], coord[1], coord[2]))
                    )  # copy this when it works below.
                    minx = min(minx, parent_coord.x)
                    miny = min(miny, parent_coord.y)
                    minz = min(minz, parent_coord.z)
                    maxx = max(maxx, parent_coord.x)
                    maxy = max(maxy, parent_coord.y)
                    maxz = max(maxz, parent_coord.z)
                # bpy.data.meshes.remove(mesh)
            if ob.type == 'CURVE':
                object_eval.to_mesh_clear()

    if obcount == 0:
        minx, miny, minz, maxx, maxy, maxz = 0, 0, 0, 0, 0, 0

    minx *= parent.scale.x
    maxx *= parent.scale.x
    miny *= parent.scale.y
    maxy *= parent.scale.y
    minz *= parent.scale.z
    maxz *= parent.scale.z

    return minx, miny, minz, maxx, maxy, maxz


def get_bounds_worldspace(obs, use_modifiers=False):
    # progress('getting bounds of object(s)')
    maxx = maxy = maxz = -10000000
    minx = miny = minz = 10000000
    obcount = 0  # calculates the mesh obs. Good for non-mesh objects
    for ob in obs:
        # bb=ob.bound_box
        mw = ob.matrix_world
        if ob.type == 'MESH' or ob.type == 'CURVE':
            depsgraph = bpy.context.evaluated_depsgraph_get()
            ob_eval = ob.evaluated_get(depsgraph)
            mesh = ob_eval.to_mesh()
            obcount += 1
            if mesh is not None:
                for c in mesh.vertices:
                    coord = c.co
                    world_coord = mw @ Vector((coord[0], coord[1], coord[2]))
                    minx = min(minx, world_coord.x)
                    miny = min(miny, world_coord.y)
                    minz = min(minz, world_coord.z)
                    maxx = max(maxx, world_coord.x)
                    maxy = max(maxy, world_coord.y)
                    maxz = max(maxz, world_coord.z)
            ob_eval.to_mesh_clear()

    if obcount == 0:
        minx, miny, minz, maxx, maxy, maxz = 0, 0, 0, 0, 0, 0
    return minx, miny, minz, maxx, maxy, maxz


def is_linked_asset(ob):
    return ob.get('asset_data') and ob.instance_collection is not None


def get_dimensions(obs):
    minx, miny, minz, maxx, maxy, maxz = get_bounds_snappable(obs)
    bbmin = Vector((minx, miny, minz))
    bbmax = Vector((maxx, maxy, maxz))
    dim = Vector((maxx - minx, maxy - miny, maxz - minz))
    return dim, bbmin, bbmax


def get_headers(
        correlation_id: str = None,
        api_key: str = None,
        include_id_token: bool = False,
) -> dict:
    headers = {
        'accept': 'application/json',
        'X-Request-Id': str(uuid.uuid4())
    }
    if correlation_id:
        headers['X-Correlation-Id'] = correlation_id
    if api_key is None:
        api_key = bpy.context.preferences.addons['hana3d'].preferences.api_key
    if api_key != '':
        headers["Authorization"] = "Bearer %s" % api_key
    if include_id_token:
        id_token = bpy.context.preferences.addons['hana3d'].preferences.id_token
        headers['X-ID-Token'] = id_token
    return headers


def scale_2d(v, s, p):
    '''scale a 2d vector with a pivot'''
    return (p[0] + s[0] * (v[0] - p[0]), p[1] + s[1] * (v[1] - p[1]))


def scale_uvs(ob, scale=1.0, pivot=Vector((0.5, 0.5))):
    mesh = ob.data
    if len(mesh.uv_layers) > 0:
        uv = mesh.uv_layers[mesh.uv_layers.active_index]

        # Scale a UV map iterating over its coordinates to a given scale and with a pivot point
        for uvindex in range(len(uv.data)):
            uv.data[uvindex].uv = scale_2d(uv.data[uvindex].uv, scale, pivot)


# map uv cubic and switch of auto tex space and set it to 1,1,1
def automap(target_object=None, target_slot=None, tex_size=1, bg_exception=False, just_scale=False):
    s = bpy.context.scene
    mat_props = s.hana3d_mat
    if mat_props.automap:
        tob = bpy.data.objects[target_object]
        # only automap mesh models
        if tob.type == 'MESH':
            actob = bpy.context.active_object
            bpy.context.view_layer.objects.active = tob

            # auto tex space
            if tob.data.use_auto_texspace:
                tob.data.use_auto_texspace = False

            if not just_scale:
                tob.data.texspace_size = (1, 1, 1)

            if 'automap' not in tob.data.uv_layers:
                bpy.ops.mesh.uv_texture_add()
                uvl = tob.data.uv_layers[-1]
                uvl.name = 'automap'

            # TODO limit this to active material
            # tob.data.uv_textures['automap'].active = True

            scale = tob.scale.copy()

            if target_slot is not None:
                tob.active_material_index = target_slot
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='DESELECT')

            # this exception is just for a 2.8 background thunmbnailer crash,
            # can be removed when material slot select works...
            if bg_exception:
                bpy.ops.mesh.select_all(action='SELECT')
            else:
                bpy.ops.object.material_slot_select()

            scale = (scale.x + scale.y + scale.z) / 3.0
            if not just_scale:
                # it's * 2.0 because blender can't tell size of a unit cube :)
                bpy.ops.uv.cube_project(cube_size=scale * 2.0 / (tex_size), correct_aspect=False)

            bpy.ops.object.editmode_toggle()
            tob.data.uv_layers.active = tob.data.uv_layers['automap']
            tob.data.uv_layers["automap"].active_render = True
            # this by now works only for thumbnail preview,
            # but should be extended to work on arbitrary objects.
            # by now, it takes the basic uv map = 1 meter. also,
            # it now doeasn't respect more materials on one object,
            # it just scales whole UV.
            if just_scale:
                scale_uvs(tob, scale=Vector((1 / tex_size, 1 / tex_size)))
            bpy.context.view_layer.objects.active = actob


def name_update():
    asset = get_active_asset()
    props = asset.hana3d
    if asset is None:
        return
    if props.name_old != props.name:
        props.name_changed = True
        props.name_old = props.name
        nname = props.name.strip()
        nname = nname.replace('_', ' ')

        if nname.isupper():
            nname = nname.lower()
        nname = nname[0].upper() + nname[1:]
        props.name = nname
        # here we need to fix the name for blender data = ' or "
        # give problems in path evaluation down the road.
    fname = props.name
    fname = fname.replace('\'', '')
    fname = fname.replace('\"', '')
    asset.name = fname


def params_to_dict(params):
    params_dict = {}
    for p in params:
        params_dict[p['parameterType']] = p['value']
    return params_dict


def dict_to_params(inputs, parameters=None):
    if parameters is None:
        parameters = []
    for k in inputs.keys():
        if type(inputs[k]) == list:
            strlist = ""
            for idx, s in enumerate(inputs[k]):
                strlist += s
                if idx < len(inputs[k]) - 1:
                    strlist += ','

            value = "%s" % strlist
        elif type(inputs[k]) != bool:
            value = inputs[k]
        else:
            value = str(inputs[k])
        parameters.append({"parameterType": k, "value": value})
    return parameters


def user_logged_in():
    a = bpy.context.window_manager.get('hana3d profile')
    if a is not None:
        return True
    return False


def profile_is_validator():
    a = bpy.context.window_manager.get('hana3d profile')
    if a is not None and a['user'].get('exmenu'):
        return True
    return False


def guard_from_crash():
    '''Blender tends to crash when trying to run some functions
    with the addon going through unregistration process.'''
    if bpy.context.preferences.addons.get('hana3d') is None:
        return False
    if bpy.context.preferences.addons['hana3d'].preferences is None:
        return False
    return True


def _check_for_position(obj):
    return obj.visible_get() and obj.type not in ('EMPTY', 'CAMERA')


def apply_modifiers(objects):
    bpy.ops.object.select_all(action='DESELECT')
    for obj in objects:
        if isinstance(obj.data, bpy.types.Mesh) and obj.modifiers:
            bpy.context.view_layer.objects.active = obj
            obj.select_set(True)
    if bpy.context.selected_objects:
        bpy.ops.object.convert()


def apply_rotations(objects):
    bpy.ops.object.select_all(action='DESELECT')
    for obj in objects:
        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)
        # Apply only one object at a time because some object types can't have rotation applied
        try:
            bpy.ops.object.transform_apply(
                location=False,
                rotation=True,
                scale=False,
                properties=False
            )
        except RuntimeError:
            pass
        obj.select_set(False)


def get_loc_dim(list_objects: List[bpy.types.Object]) -> Tuple[Vector, Vector]:
    vertices = []
    for obj in list_objects:
        for corner in obj.bound_box:
            vertices.append(obj.matrix_world @ Vector(corner))
    min_x = min(vertex.x for vertex in vertices)
    min_y = min(vertex.y for vertex in vertices)
    min_z = min(vertex.z for vertex in vertices)
    max_x = max(vertex.x for vertex in vertices)
    max_y = max(vertex.y for vertex in vertices)
    max_z = max(vertex.z for vertex in vertices)

    location = Vector([(max_x + min_x) / 2, (max_y + min_y) / 2, (max_z + min_z) / 2])
    dimensions = Vector([max_x - min_x, max_y - min_y, max_z - min_z])

    return location, dimensions


def get_translation_to_center(objects):
    valid_objects = [obj for obj in objects if _check_for_position(obj)]
    location, dimensions = get_loc_dim(valid_objects)
    final_location = Vector([0, 0, dimensions.z / 2])

    return final_location - location


def apply_translation(objects, translation):
    for obj in objects:
        if obj.parent is None:
            obj.location += translation


def copy_object(obj):
    new_object = obj.copy()
    if obj.data is not None:
        new_object.data = obj.data.copy()
    bpy.context.collection.objects.link(new_object)

    return new_object


def clear_parents(objects):
    # Remove parents from objects using operator to avoid errors with transformations
    bpy.ops.object.select_all(action='DESELECT')
    bpy.context.view_layer.objects.active = objects[0]
    for obj in objects:
        obj.select_set(True)
    bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')


def centralize(objects):
    """Centralize a group of objects so that their median position in X and Y axis is zero and
    it "touches" the Z plane from above. Ignores position of hidden objects and cameras/empties"""
    copied_objects = [copy_object(obj) for obj in objects]
    apply_modifiers(copied_objects)
    clear_parents(copied_objects)
    apply_rotations(copied_objects)
    translation = get_translation_to_center(copied_objects)

    for obj in copied_objects:
        bpy.data.objects.remove(obj)

    apply_translation(objects, translation)


def check_meshprops(props, obs) -> Tuple[int, int]:
    '''Return face count and render face count '''
    fc = 0
    fcr = 0

    for ob in obs:
        if ob.type == 'MESH' or ob.type == 'CURVE':
            ob_eval = None
            if ob.type == 'CURVE':
                # depsgraph = bpy.context.evaluated_depsgraph_get()
                # object_eval = ob.evaluated_get(depsgraph)
                mesh = ob.to_mesh()
            else:
                mesh = ob.data
            fco = len(mesh.polygons)
            fc += fco
            fcor = fco

            for m in ob.modifiers:
                if m.type == 'SUBSURF' or m.type == 'MULTIRES':
                    fcor *= 4 ** m.render_levels
                # this is rough estimate, not to waste time with evaluating all nonmanifold edges
                if m.type == 'SOLIDIFY':
                    fcor *= 2
                if m.type == 'ARRAY':
                    fcor *= m.count
                if m.type == 'MIRROR':
                    fcor *= 2
                if m.type == 'DECIMATE':
                    fcor *= m.ratio
            fcr += fcor

            if ob_eval:
                ob_eval.to_mesh_clear()

    return fc, fcr


def fill_object_metadata(obj: bpy.types.Object):
    """ call all analysis functions """
    obs = get_hierarchy(obj)
    props = obj.hana3d

    dim, bbox_min, bbox_max = get_dimensions(obs)
    props.dimensions = dim
    props.bbox_min = bbox_min
    props.bbox_max = bbox_max

    props.face_count, props.face_count_render = check_meshprops(props, obs)
    props.object_count = len(obs)
