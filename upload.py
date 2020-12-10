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
import json
import logging
import os
import subprocess
import tempfile
import uuid
from typing import List

import bpy
import requests
from bpy.props import BoolProperty, EnumProperty
from bpy.types import Operator

from .config import HANA3D_DESCRIPTION, HANA3D_NAME
from .report_tools import execute_wrapper
from .src.ui.main import UI

from . import bg_blender, hana3d_types, logger, paths, render, rerequests, utils  # isort:skip


HANA3D_EXPORT_DATA_FILE = HANA3D_NAME + "_data.json"


def get_upload_location(props, context):
    if props.asset_type.upper() == 'MODEL':
        if context.view_layer.objects.active is not None:
            ob = utils.get_active_model()
            return ob.location
    elif props.asset_type.upper() == 'SCENE':
        return None
    elif props.asset_type.upper() == 'MATERIAL':
        if (
            context.view_layer.objects.active is not None
            and context.active_object.active_material is not None
        ):
            return context.active_object.location
    return None


def get_export_data(
    props: hana3d_types.Props,
    path_computing: str = 'uploading',
    path_state: str = 'upload_state',
):
    export_data = {
        "type": props.asset_type,
        "thumbnail_path": bpy.path.abspath(props.thumbnail),
    }
    upload_params = {}
    if props.asset_type.upper() == 'MODEL':
        # Prepare to save the file
        mainmodel = utils.get_active_model(bpy.context)

        obs = utils.get_hierarchy(mainmodel)
        obnames = []
        for ob in obs:
            obnames.append(ob.name)
        export_data["type"] = 'MODEL'
        export_data["models"] = obnames

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
        }

    elif props.asset_type.upper() == 'SCENE':
        # Prepare to save the file
        name = bpy.context.scene.name

        export_data["type"] = 'SCENE'
        export_data["scene"] = name

        eval_path = f"bpy.data.scenes['{name}']"

        upload_data = {
            "assetType": 'scene',
        }
        upload_params = {
            # TODO add values
            # "faceCount": 1,  # props.face_count,
            # "faceCountRender": 1,  # props.face_count_render,
            # "objectCount": 1,  # props.object_count,
        }

    elif props.asset_type.upper() == 'MATERIAL':
        mat = bpy.context.active_object.active_material

        export_data["type"] = 'MATERIAL'
        export_data["material"] = str(mat.name)

        eval_path = f"bpy.data.materials['{mat.name}']"

        upload_data = {
            "assetType": 'material',
        }

        upload_params = {}
    else:
        raise Exception(f'Unexpected asset_type={props.asset_type}')

    bg_process_params = {
        'eval_path_computing': f'{eval_path}.{HANA3D_NAME}.{path_computing}',
        'eval_path_state': f'{eval_path}.{HANA3D_NAME}.{path_state}',
        'eval_path': eval_path,
    }

    upload_data["sourceAppName"] = "blender"
    upload_data["sourceAppVersion"] = '{}.{}.{}'.format(*utils.get_addon_version())
    upload_data["addonVersion"] = '{}.{}.{}'.format(*utils.get_addon_blender_version())

    upload_data["name"] = props.name
    upload_data["description"] = props.description

    upload_data['parameters'] = upload_params

    upload_data["is_public"] = props.is_public
    if props.workspace != '' and not props.is_public:
        upload_data['workspace'] = props.workspace

    metadata = {}
    if hasattr(props, 'custom_props'):
        metadata.update(props.custom_props)
    if metadata:
        upload_data['metadata'] = metadata

    upload_data['tags'] = []
    for tag in props.tags_list.keys():
        if props.tags_list[tag].selected is True:
            upload_data["tags"].append(tag)

    upload_data['libraries'] = []
    for library in props.libraries_list.keys():
        if props.libraries_list[library].selected is True:
            library_id = props.libraries_list[library].id_
            library = {}
            library.update({
                'id': library_id,
            })
            if props.custom_props.keys() != []:
                custom_props = {}
                for name in props.custom_props.keys():
                    value = props.custom_props[name]
                    slug = props.custom_props_info[name]['slug']
                    prop_library_id = props.custom_props_info[name]['library_id']
                    if prop_library_id == library_id:
                        custom_props.update({slug: value})
                library.update({'metadata': {'view_props': custom_props}})
            upload_data['libraries'].append(library)

    export_data['publish_message'] = props.publish_message

    return export_data, upload_data, bg_process_params


asset_types = (
    ('MODEL', 'Model', 'set of objects'),
    ('SCENE', 'Scene', 'scene'),
    ('MATERIAL', 'Material', 'any .blend Material'),
    ('ADDON', 'Addon', 'addnon'),
)


class UploadOperator(Operator):
    """Tooltip"""

    bl_idname = f"object.{HANA3D_NAME}_upload"
    bl_description = f"Upload or re-upload asset + thumbnail + metadata to {HANA3D_DESCRIPTION}"

    bl_label = "hana3d asset upload"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    # type of upload - model, material, textures, e.t.c.
    asset_type: EnumProperty(
        name="Type",
        items=asset_types,
        description="Type of upload",
        default="MODEL",
    )

    reupload: BoolProperty(
        name="reupload",
        description="reupload but also draw so that it asks what to reupload",
        default=False,
        options={'SKIP_SAVE'},
    )

    metadata: BoolProperty(name="metadata", default=True, options={'SKIP_SAVE'})

    thumbnail: BoolProperty(name="thumbnail", default=False, options={'SKIP_SAVE'})

    main_file: BoolProperty(name="main file", default=False, options={'SKIP_SAVE'})

    @classmethod
    def poll(cls, context):
        props = utils.get_upload_props()
        return bpy.context.view_layer.objects.active is not None and not props.uploading

    @execute_wrapper
    def execute(self, context):
        obj = utils.get_active_asset()
        props = getattr(obj, HANA3D_NAME)

        if self.asset_type == 'MODEL':
            utils.fill_object_metadata(obj)

        upload_set = ['METADATA', 'MAINFILE']
        if props.has_thumbnail:
            upload_set.append('THUMBNAIL')
            props.remote_thumbnail = False
        else:
            props.remote_thumbnail = True

        return self.start_upload(context, props, upload_set)

    def draw(self, context):
        props = utils.get_upload_props()
        layout = self.layout

        if self.reupload:
            # layout.prop(self, 'metadata')
            layout.prop(self, 'main_file')
            layout.prop(self, 'thumbnail')

        if props.view_id != '' and not self.reupload:
            layout.label(text="Really upload as new? ")
            layout.label(text="Do this only when you create a new asset from an old one.")
            layout.label(text="For updates of thumbnail or model use reupload.")

    def start_upload(self, context, props: hana3d_types.Props, upload_set: List[str]):  # noqa D102,WPS212,WPS210,WPS213,WPS231,E501
        utils.name_update()

        location = get_upload_location(props, context)
        ui = UI()
        ui.add_report(text='preparing upload')

        if 'jobs' not in props.render_data:
            props.render_data['jobs'] = []

        if not self.reupload:
            props.view_id = ''
            props.id = ''
        export_data, upload_data, bg_process_params = get_export_data(props)

        workspace = props.workspace

        # weird array conversion only for upload, not for tooltips.
        upload_data['parameters'] = utils.dict_to_params(upload_data['parameters'])

        binary_path = bpy.app.binary_path
        script_path = os.path.dirname(os.path.realpath(__file__))
        basename, ext = os.path.splitext(bpy.data.filepath)
        # if not basename:
        #     basename = os.path.join(basename, "temp")
        if not ext:
            ext = ".blend"
        tempdir = tempfile.mkdtemp()
        datafile = os.path.join(tempdir, HANA3D_EXPORT_DATA_FILE)

        if 'THUMBNAIL' in upload_set and not os.path.exists(export_data['thumbnail_path']):
            ui.add_report(text='Thumbnail not found')
            props.uploading = False
            return {'CANCELLED'}

        correlation_id = str(uuid.uuid4())
        headers = rerequests.get_headers(correlation_id)

        if props.id == '':
            url = paths.get_api_url('assets')
            try:
                response = rerequests.post(
                    url,
                    json=upload_data,
                    headers=headers,
                    immediate=True,
                )
                ui.add_report(text='uploaded metadata')

                dict_response = response.json()
                logging.debug(dict_response)
                props.id = dict_response['id']
            except requests.exceptions.RequestException as e:
                logging.error(e)
                ui.add_report(text=str(e))
                props.uploading = False
                return {'CANCELLED'}
        else:
            url = paths.get_api_url('assets', props.id)
            try:
                rerequests.put(
                    url,
                    json=upload_data,
                    headers=headers,
                    immediate=True,
                )
                ui.add_report(text='uploaded metadata')
            except requests.exceptions.RequestException as e:
                logging.error(e)
                ui.add_report(text=str(e))
                props.uploading = False
                return {'CANCELLED'}

        if upload_set == ['METADATA']:
            props.uploading = False
            ui.add_report(text='upload finished successfully')
            props.view_workspace = workspace
            return {'FINISHED'}

        if self.reupload:
            upload_data['id_parent'] = props.view_id
        props.view_id = str(uuid.uuid4())
        upload_data['viewId'] = props.view_id
        upload_data['id'] = props.id

        source_filepath = os.path.join(tempdir, "export_hana3d" + ext)
        clean_file_path = paths.get_clean_filepath()
        data = {
            'clean_file_path': clean_file_path,
            'source_filepath': source_filepath,
            'temp_dir': tempdir,
            'export_data': export_data,
            'upload_data': upload_data,
            'upload_set': upload_set,
            'correlation_id': correlation_id,
        }

        try:
            props.uploading = True
            autopack = bpy.data.use_autopack is True
            if autopack:
                bpy.ops.file.autopack_toggle()
            bpy.ops.wm.save_as_mainfile(filepath=source_filepath, compress=False, copy=True)

            with open(datafile, 'w') as s:
                json.dump(data, s)

            skip_post_process = 'false'
            if any(len(mesh.uv_layers) > 1 for mesh in bpy.data.meshes):
                ui = UI()
                ui.add_report(
                    'GLB and USDZ will not be generated: at least 1 mesh has more than 1 UV Map',
                )
                skip_post_process = 'true'

            proc = subprocess.Popen(
                [
                    binary_path,
                    "--background",
                    "-noaudio",
                    clean_file_path,
                    "--python",
                    os.path.join(script_path, "upload_bg.py"),
                    "--",
                    datafile,
                    HANA3D_NAME,
                    skip_post_process,
                ],
                bufsize=5000,
                stdout=subprocess.PIPE,
                stdin=subprocess.PIPE,
            )

            bg_blender.add_bg_process(
                process_type='UPLOAD',
                process=proc,
                location=location,
                **bg_process_params,
            )

            if autopack:
                bpy.ops.file.autopack_toggle()

        except Exception as error:
            ui.add_report(text=str(error))
            props.uploading = False
            logging.error(error)
            return {'CANCELLED'}

        if props.remote_thumbnail:
            thread = render.RenderThread(
                props,
                engine='CYCLES',
                frame_start=1,
                frame_end=1,
                is_thumbnail=True,
            )
            thread.start()
            render.render_threads.append(thread)

        props.view_workspace = workspace
        return {'FINISHED'}


classes = (
    UploadOperator,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
