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

    paths = reload(paths)
    utils = reload(utils)
    bg_blender = reload(bg_blender)
    autothumb = reload(autothumb)
    version_checker = reload(version_checker)
    ui = reload(ui)
    overrides = reload(overrides)
    rerequests = reload(rerequests)
else:
    from hana3d import (
        paths,
        utils,
        bg_blender,
        autothumb,
        version_checker,
        ui,
        overrides,
        rerequests,
    )

import json
import os
import re
import subprocess
import tempfile
import threading

import bpy
import requests
from bpy.props import (
    BoolProperty,
    EnumProperty,
    StringProperty
)
from bpy.types import Operator

HANA3D_EXPORT_DATA_FILE = "data.json"


def comma2array(text):
    commasep = text.split(',')
    ar = []
    for i, s in enumerate(commasep):
        s = s.strip()
        if s != '':
            ar.append(s)
    return ar


def get_app_version():
    ver = bpy.app.version
    return '%i.%i.%i' % (ver[0], ver[1], ver[2])


def add_version(data):
    app_version = get_app_version()
    addon_version = version_checker.get_addon_version()
    data["sourceAppName"] = "blender"
    data["sourceAppVersion"] = app_version
    data["addonVersion"] = addon_version


def write_to_report(props, text):
    props.report = props.report + text + '\n'


def get_missing_data_model(props):
    props.report = ''
    autothumb.update_upload_model_preview(None, None)

    if props.name == '':
        write_to_report(props, 'Set model name')
    # if props.tags == '':
    #     write_to_report(props, 'Write at least 3 tags')
    if not props.has_thumbnail:
        write_to_report(props, 'Add thumbnail:')

        props.report += props.thumbnail_generating_state + '\n'
    if not any(props.dimensions):
        write_to_report(props, 'Run autotags operator or fill in dimensions manually')


def get_missing_data_scene(props):
    props.report = ''
    autothumb.update_upload_scene_preview(None, None)

    if props.name == '':
        write_to_report(props, 'Set scene name')
    if not props.has_thumbnail:
        write_to_report(props, 'Add thumbnail:')
        props.report += props.thumbnail_generating_state + '\n'


def get_missing_data_material(props):
    props.report = ''
    autothumb.update_upload_material_preview(None, None)
    if props.name == '':
        write_to_report(props, 'Set material name')
    # if props.tags == '':
    #     write_to_report(props, 'Write at least 3 tags')
    if not props.has_thumbnail:
        write_to_report(props, 'Add thumbnail:')
        props.report += props.thumbnail_generating_state


def sub_to_camel(content):
    replaced = re.sub(r"_.", lambda m: m.group(0)[1].upper(), content)
    return replaced


def camel_to_sub(content):
    replaced = re.sub(r"[A-Z]", lambda m: '_' + m.group(0).lower(), content)
    return replaced


def get_upload_data(self, context, asset_type):
    export_data = {
        "type": asset_type,
    }
    upload_params = {}
    if asset_type == 'MODEL':
        # Prepare to save the file
        mainmodel = utils.get_active_model()

        props = mainmodel.hana3d

        obs = utils.get_hierarchy(mainmodel)
        obnames = []
        for ob in obs:
            obnames.append(ob.name)
        export_data["models"] = obnames
        export_data["thumbnail_path"] = bpy.path.abspath(props.thumbnail)

        eval_path_computing = "bpy.data.objects['%s'].hana3d.uploading" % mainmodel.name
        eval_path_state = "bpy.data.objects['%s'].hana3d.upload_state" % mainmodel.name
        eval_path = "bpy.data.objects['%s']" % mainmodel.name

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

    if asset_type == 'SCENE':
        # Prepare to save the file
        s = bpy.context.scene

        props = s.hana3d

        export_data["scene"] = s.name
        export_data["thumbnail_path"] = bpy.path.abspath(props.thumbnail)

        eval_path_computing = "bpy.data.scenes['%s'].hana3d.uploading" % s.name
        eval_path_state = "bpy.data.scenes['%s'].hana3d.upload_state" % s.name
        eval_path = "bpy.data.scenes['%s']" % s.name

        upload_data = {
            "assetType": 'scene',
        }
        upload_params = {
            # TODO fix fixed values
            "faceCount": 1,  # props.face_count,
            "faceCountRender": 1,  # props.face_count_render,
            "objectCount": 1,  # props.object_count,
        }

    elif asset_type == 'MATERIAL':
        mat = bpy.context.active_object.active_material
        props = mat.hana3d

        # props.name = mat.name

        export_data["material"] = str(mat.name)
        export_data["thumbnail_path"] = bpy.path.abspath(props.thumbnail)

        eval_path_computing = "bpy.data.materials['%s'].hana3d.uploading" % mat.name
        eval_path_state = "bpy.data.materials['%s'].hana3d.upload_state" % mat.name
        eval_path = "bpy.data.materials['%s']" % mat.name

        upload_data = {
            "assetType": 'material',
        }

        upload_params = {}

    add_version(upload_data)

    upload_data["name"] = props.name
    upload_data["description"] = props.description
    upload_data["tags"] = comma2array(props.tags)

    if props.asset_base_id != '':
        upload_data['assetBaseId'] = props.asset_base_id
        upload_data['id'] = props.id

    upload_data['parameters'] = upload_params

    upload_data["is_public"] = props.is_public
    if props.workspace != '' and not props.is_public:
        upload_data['workspace'] = props.workspace

    metadata = {}
    list_clients = getattr(props, 'client', '').split(',')
    list_skus = getattr(props, 'sku', '').split(',')
    product_info = [{'client': client, 'sku': sku} for client, sku in zip(list_clients, list_skus)]
    if len(product_info) > 0:
        metadata['product_info'] = product_info
    if hasattr(props, 'custom_props'):
        metadata.update(props.custom_props)
    if metadata:
        upload_data['metadata'] = metadata

    export_data['publish_message'] = props.publish_message

    return export_data, upload_data, eval_path_computing, eval_path_state, eval_path, props


def validate_upload_data(props):
    list_clients = getattr(props, 'client', '').split(',')
    list_skus = getattr(props, 'sku', '').split(',')

    assert len(list_clients) == len(list_skus), 'Number of clients must be the same as number of SKUs'  # noqa E501


def verification_status_change_thread(asset_id, state):
    upload_data = {"verificationStatus": state}
    url = paths.get_api_url() + 'assets/' + str(asset_id) + '/'
    headers = utils.get_headers()
    try:
        rerequests.patch(url, json=upload_data, headers=headers, verify=True)
    except requests.exceptions.RequestException as e:
        print(e)
        return {'CANCELLED'}
    return {'FINISHED'}


def get_upload_location(props):
    scene = bpy.context.scene
    ui_props = scene.Hana3DUI
    if ui_props.asset_type == 'MODEL':
        if bpy.context.view_layer.objects.active is not None:
            ob = utils.get_active_model()
            return ob.location
    if ui_props.asset_type == 'SCENE':
        return None
    elif ui_props.asset_type == 'MATERIAL':
        if (
            bpy.context.view_layer.objects.active is not None
            and bpy.context.active_object.active_material is not None
        ):
            return bpy.context.active_object.location
    return None


def auto_fix(asset_type=''):
    # this applies various procedures to ensure coherency in the database.
    asset = utils.get_active_asset()
    props = utils.get_upload_props()
    if asset_type == 'MATERIAL':
        overrides.ensure_eevee_transparency(asset)
        asset.name = props.name


def start_upload(self, context, asset_type, reupload, upload_set):
    '''start upload process, by processing data'''

    # fix the name first
    utils.name_update()

    props = utils.get_upload_props()

    location = get_upload_location(props)
    props.upload_state = 'preparing upload'

    auto_fix(asset_type=asset_type)

    # do this for fixing long tags in some upload cases
    props.tags = props.tags[:]

    props.name = props.name.strip()
    # TODO  move this to separate function
    # check for missing metadata
    if asset_type == 'MODEL':
        get_missing_data_model(props)
    if asset_type == 'SCENE':
        get_missing_data_scene(props)
    elif asset_type == 'MATERIAL':
        get_missing_data_material(props)

    if props.report != '':
        self.report({'ERROR_INVALID_INPUT'}, props.report)
        return {'CANCELLED'}

    if not reupload:
        props.asset_base_id = ''
        props.id = ''
    (
        export_data,
        upload_data,
        eval_path_computing,
        eval_path_state,
        eval_path,
        props,
    ) = get_upload_data(self, context, asset_type)
    # We have to validate here as get_upload_data() is called in other parts of the code
    validate_upload_data(props)
    # utils.pprint(upload_data)
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
    source_filepath = os.path.join(tempdir, "export_hana3d" + ext)
    clean_file_path = paths.get_clean_filepath()
    data = {
        'clean_file_path': clean_file_path,
        'source_filepath': source_filepath,
        'temp_dir': tempdir,
        'export_data': export_data,
        'upload_data': upload_data,
        'debug_value': bpy.app.debug_value,
        'upload_set': upload_set,
    }
    datafile = os.path.join(tempdir, HANA3D_EXPORT_DATA_FILE)

    # check if thumbnail exists:
    if 'THUMBNAIL' in upload_set:
        if not os.path.exists(export_data["thumbnail_path"]):
            props.upload_state = 'Thumbnail not found'
            props.uploading = False
            return {'CANCELLED'}

    # first upload metadata to server, so it can be saved inside the current file
    url = paths.get_api_url() + 'assets/'

    headers = utils.get_headers()

    json_metadata = upload_data  # json.dumps(upload_data, ensure_ascii=False).encode('utf8')
    global reports
    if props.asset_base_id == '':
        try:
            r = rerequests.post(
                url,
                json=json_metadata,
                headers=headers,
                verify=True,
                immediate=True
            )
            ui.add_report('uploaded metadata')
            utils.p(r.text)
        except requests.exceptions.RequestException as e:
            print(e)
            props.upload_state = str(e)
            props.uploading = False
            return {'CANCELLED'}

    else:
        url += props.id + '/'
        try:
            if 'MAINFILE' in upload_set:
                json_metadata["verificationStatus"] = "uploading"
            r = rerequests.put(
                url,
                json=json_metadata,
                headers=headers,
                verify=True,
                immediate=True
            )
            ui.add_report('uploaded metadata')
            # parse the request
            # print('uploaded metadata')
            # print(r.text)
        except requests.exceptions.RequestException as e:
            print(e)
            props.upload_state = str(e)
            props.uploading = False
            return {'CANCELLED'}

    # props.upload_state = 'step 1'
    if upload_set == ['METADATA']:
        props.uploading = False
        props.upload_state = 'upload finished successfully'
        return {'FINISHED'}
    try:
        rj = r.json()
        utils.pprint(rj)
        # if r.status_code not in (200, 201):
        #     if r.status_code == 401:
        #         ui.add_report(r.detail, 5, colors.RED)
        #     return {'CANCELLED'}
        props.asset_base_id = rj['assetBaseId']
        props.id = rj['id']
        upload_data['assetBaseId'] = props.asset_base_id
        upload_data['id'] = props.id

        # bpy.ops.wm.save_mainfile()
        # bpy.ops.wm.save_as_mainfile(filepath=filepath, compress=False, copy=True)

        props.uploading = True
        # save a copy of actual scene but don't interfere with the users models
        autopack = False
        if bpy.data.use_autopack is True:
            autopack = True
            bpy.ops.file.autopack_toggle()
        bpy.ops.wm.save_as_mainfile(filepath=source_filepath, compress=False, copy=True)

        with open(datafile, 'w') as s:
            json.dump(data, s)

        proc = subprocess.Popen(
            [
                binary_path,
                "--background",
                "-noaudio",
                clean_file_path,
                "--python",
                os.path.join(script_path, "upload_bg.py"),
                "--",
                datafile,  # ,filepath, tempdir
            ],
            bufsize=5000,
            stdout=subprocess.PIPE,
            stdin=subprocess.PIPE,
        )

        bg_blender.add_bg_process(
            eval_path_computing=eval_path_computing,
            eval_path_state=eval_path_state,
            eval_path=eval_path,
            process_type='UPLOAD',
            process=proc,
            location=location,
        )

        if autopack is True:
            bpy.ops.file.autopack_toggle()

    except Exception as e:
        props.upload_state = str(e)
        props.uploading = False
        print(e)
        return {'CANCELLED'}

    return {'FINISHED'}


asset_types = (
    ('MODEL', 'Model', 'set of objects'),
    ('SCENE', 'Scene', 'scene'),
    ('MATERIAL', 'Material', 'any .blend Material'),
    ('ADDON', 'Addon', 'addnon'),
)


class UploadOperator(Operator):
    """Tooltip"""

    bl_idname = "object.hana3d_upload"
    bl_description = "Upload or re-upload asset + thumbnail + metadata"

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
        return bpy.context.view_layer.objects.active is not None

    def execute(self, context):
        bpy.ops.object.hana3d_auto_tags()

        upload_set = ['METADATA', 'THUMBNAIL', 'MAINFILE']

        result = start_upload(self, context, self.asset_type, self.reupload, upload_set)

        return result

    def draw(self, context):
        props = utils.get_upload_props()
        layout = self.layout

        if self.reupload:
            # layout.prop(self, 'metadata')
            layout.prop(self, 'main_file')
            layout.prop(self, 'thumbnail')

        if props.asset_base_id != '' and not self.reupload:
            layout.label(text="Really upload as new? ")
            layout.label(text="Do this only when you create a new asset from an old one.")
            layout.label(text="For updates of thumbnail or model use reupload.")

    def invoke(self, context, event):
        # props = utils.get_upload_props()

        # if not utils.user_logged_in():
        #     ui_panels.draw_not_logged_in(self)
        #     return {'CANCELLED'}

        return self.execute(context)


class AssetVerificationStatusChange(Operator):
    """Change verification status"""

    bl_idname = "object.hana3d_change_status"
    bl_description = "Change asset ststus"
    bl_label = "Change verification status"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    # type of upload - model, material, textures, e.t.c.
    asset_id: StringProperty(name="asset id",)

    state: StringProperty(name="verification_status", default='uploaded')

    @classmethod
    def poll(cls, context):
        return True

    def draw(self, context):
        layout = self.layout
        # if self.state == 'deleted':
        layout.label(text='Really delete asset from hana3d online storage?')
        # layout.prop(self, 'state')

    def execute(self, context):
        # update status in search results for validator's clarity
        sr = bpy.context.scene['search results']
        sro = bpy.context.scene['search results orig']['results']

        for r in sr:
            if r['id'] == self.asset_id:
                r['verification_status'] = self.state
        for r in sro:
            if r['id'] == self.asset_id:
                r['verificationStatus'] = self.state

        thread = threading.Thread(
            target=verification_status_change_thread,
            args=(self.asset_id, self.state)
        )
        thread.start()
        return {'FINISHED'}

    def invoke(self, context, event):
        print(self.state)
        if self.state == 'deleted':
            wm = context.window_manager
            return wm.invoke_props_dialog(self)


def register_upload():
    bpy.utils.register_class(UploadOperator)
    bpy.utils.register_class(AssetVerificationStatusChange)


def unregister_upload():
    bpy.utils.unregister_class(UploadOperator)
    bpy.utils.unregister_class(AssetVerificationStatusChange)
