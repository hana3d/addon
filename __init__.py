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

bl_info = {
    "name": "Hana3D - BlenderKit Fork",
    "author": "Vilem Duha, Petr Dlouhy, Real2U",
    "version": (0, 4, 0),
    "blender": (2, 83, 0),
    "location": "View3D > Properties > hana3d",
    "description": "Online hana3d library (materials, models, scenes and more). Connects to the internet.",  # noqa: E501
    "warning": "",
    # "doc_url": "{BLENDER_MANUAL_URL}/addons/add_mesh/hana3d.html",
    "category": "3D View",
}

if "bpy" in locals():
    from importlib import reload

    asset_inspector = reload(asset_inspector)
    search = reload(search)
    download = reload(download)
    upload = reload(upload)
    autothumb = reload(autothumb)
    ui = reload(ui)
    icons = reload(icons)
    bg_blender = reload(bg_blender)
    paths = reload(paths)
    utils = reload(utils)
    ui_panels = reload(ui_panels)
    hana3d_oauth = reload(hana3d_oauth)
    tasks_queue = reload(tasks_queue)
    custom_props = reload(custom_props)
    render_ops = reload(render_ops)
else:
    from hana3d import (
        asset_inspector,
        search,
        download,
        upload,
        autothumb,
        ui,
        icons,
        bg_blender,
        paths,
        utils,
        ui_panels,
        hana3d_oauth,
        tasks_queue,
        custom_props,
        render_ops,
    )

import math

import bpy
import bpy.utils.previews
from bpy.app.handlers import persistent
from bpy.props import (
    BoolProperty,
    EnumProperty,
    FloatProperty,
    FloatVectorProperty,
    IntProperty,
    PointerProperty,
    StringProperty
)
from bpy.types import AddonPreferences, PropertyGroup

from . import addon_updater_ops

# logging.basicConfig(filename = 'hana3d.log', level = logging.INFO,
#                     format = '	%(asctime)s:%(filename)s:%(funcName)s:%(lineno)d:%(message)s')


@persistent
def scene_load(context):
    search.load_previews()
    ui_props = bpy.context.scene.Hana3DUI
    ui_props.assetbar_on = False
    ui_props.turn_off = False
    preferences = bpy.context.preferences.addons['hana3d'].preferences
    preferences.login_attempt = False
    preferences.refresh_in_progress = False


@bpy.app.handlers.persistent
def check_timers_timer():
    '''Checks if all timers are registered regularly.
    Prevents possible bugs from stopping the addon.
    '''
    if not bpy.app.timers.is_registered(search.timer_update):
        bpy.app.timers.register(search.timer_update)
    if not bpy.app.timers.is_registered(download.timer_update):
        bpy.app.timers.register(download.timer_update)
    if not (bpy.app.timers.is_registered(tasks_queue.queue_worker)):
        bpy.app.timers.register(tasks_queue.queue_worker)
    if not bpy.app.timers.is_registered(bg_blender.bg_update):
        bpy.app.timers.register(bg_blender.bg_update)
    return 5.0


thumbnail_angles = (
    ('DEFAULT', 'default', ''),
    ('FRONT', 'front', ''),
    ('SIDE', 'side', ''),
    ('TOP', 'top', ''),
)

thumbnail_snap = (
    ('GROUND', 'ground', ''),
    ('WALL', 'wall', ''),
    ('CEILING', 'ceiling', ''),
    ('FLOAT', 'floating', ''),
)

thumbnail_resolutions = (
    ('256', '256', ''),
    ('512', '512 - minimum for public', ''),
    ('1024', '1024', ''),
    ('2048', '2048', ''),
)


def get_upload_asset_type(self):
    typemapper = {
        Hana3DModelUploadProps: 'model',
        Hana3DSceneUploadProps: 'scene',
        Hana3DMaterialUploadProps: 'material',
    }
    asset_type = typemapper[type(self)]
    return asset_type


def switch_search_results(self, context):
    s = bpy.context.scene
    props = s.Hana3DUI
    if props.asset_type == 'MODEL':
        s['search results'] = s.get('hana3d model search')
        s['search results orig'] = s.get('hana3d model search orig')
    elif props.asset_type == 'SCENE':
        s['search results'] = s.get('hana3d scene search')
        s['search results orig'] = s.get('hana3d scene search orig')
    elif props.asset_type == 'MATERIAL':
        s['search results'] = s.get('hana3d material search')
        s['search results orig'] = s.get('hana3d material search orig')
    elif props.asset_type == 'HDR':
        s['search results'] = s.get('hana3d hdr search')
        s['search results orig'] = s.get('hana3d hdr search orig')
    search.load_previews()


def asset_type_callback(self, context):
    if self.down_up == 'SEARCH':
        items = (
            (
                'MODEL',
                'Find Models',
                'Find models in the Hana3D online database',
                'OBJECT_DATAMODE',
                0,
            ),
            ('SCENE', 'Find Scenes', 'Find scenes in the Hana3D online database', 'SCENE_DATA', 1),
            (
                'MATERIAL',
                'Find Materials',
                'Find materials in the Hana3D online database',
                'MATERIAL',
                2,
            ),
            # ('HDR', 'Find HDRs', 'Find HDRs in the Hana3D online database', 'WORLD_DATA', 3),
        )
    else:
        items = (
            ('MODEL', 'Upload Model', 'Upload a model to Hana3D', 'OBJECT_DATAMODE', 0),
            ('SCENE', 'Upload Scene', 'Upload a scene to Hana3D', 'SCENE_DATA', 1),
            ('MATERIAL', 'Upload Material', 'Upload a material to Hana3D', 'MATERIAL', 2),
            # ('HDR', 'Upload HDR', 'Upload a HDR to Hana3D', 'WORLD_DATA', 3),
        )
    return items


class Hana3DUIProps(PropertyGroup):
    down_up: EnumProperty(
        name="Download vs Upload",
        items=(
            ('SEARCH', 'Search', 'Sctivate searching', 'VIEWZOOM', 0),
            ('UPLOAD', 'Upload', 'Activate uploading', 'COPYDOWN', 1),
        ),
        description="hana3d",
        default="SEARCH",
    )
    asset_type: EnumProperty(
        name="Hana3D Active Asset Type",
        items=asset_type_callback,
        description="Activate asset in UI",
        default=None,
        update=switch_search_results,
    )
    # these aren't actually used ( by now, seems to better use globals in UI module:
    draw_tooltip: BoolProperty(name="Draw Tooltip", default=False)
    tooltip: StringProperty(name="Tooltip", description="asset preview info", default="")

    ui_scale = 1

    thumb_size_def = 96
    margin_def = 0

    thumb_size: IntProperty(name="Thumbnail Size", default=thumb_size_def, min=-1, max=256)

    margin: IntProperty(name="Margin", default=margin_def, min=-1, max=256)
    highlight_margin: IntProperty(
        name="Highlight Margin",
        default=int(margin_def / 2),
        min=-10,
        max=256
    )

    bar_height: IntProperty(
        name="Bar Height",
        default=thumb_size_def + 2 * margin_def,
        min=-1,
        max=2048
    )
    bar_x_offset: IntProperty(name="Bar X Offset", default=20, min=0, max=5000)
    bar_y_offset: IntProperty(name="Bar Y Offset", default=80, min=0, max=5000)

    bar_x: IntProperty(name="Bar X", default=100, min=0, max=5000)
    bar_y: IntProperty(name="Bar Y", default=100, min=50, max=5000)
    bar_end: IntProperty(name="Bar End", default=100, min=0, max=5000)
    bar_width: IntProperty(name="Bar Width", default=100, min=0, max=5000)

    wcount: IntProperty(name="Width Count", default=10, min=0, max=5000)
    hcount: IntProperty(name="Rows", default=5, min=0, max=5000)

    reports_y: IntProperty(name="Reports Y", default=5, min=0, max=5000)
    reports_x: IntProperty(name="Reports X", default=5, min=0, max=5000)

    assetbar_on: BoolProperty(name="Assetbar On", default=False)
    turn_off: BoolProperty(name="Turn Off", default=False)

    mouse_x: IntProperty(name="Mouse X", default=0)
    mouse_y: IntProperty(name="Mouse Y", default=0)

    active_index: IntProperty(name="Active Index", default=-3)
    scrolloffset: IntProperty(name="Scroll Offset", default=0)
    drawoffset: IntProperty(name="Draw Offset", default=0)

    dragging: BoolProperty(name="Dragging", default=False)
    drag_init: BoolProperty(name="Drag Initialisation", default=False)
    drag_length: IntProperty(name="Drag length", default=0)
    draw_drag_image: BoolProperty(name="Draw Drag Image", default=False)
    draw_snapped_bounds: BoolProperty(name="Draw Snapped Bounds", default=False)

    snapped_location: FloatVectorProperty(name="Snapped Location", default=(0, 0, 0))
    snapped_bbox_min: FloatVectorProperty(name="Snapped Bbox Min", default=(0, 0, 0))
    snapped_bbox_max: FloatVectorProperty(name="Snapped Bbox Max", default=(0, 0, 0))
    snapped_normal: FloatVectorProperty(name="Snapped Normal", default=(0, 0, 0))

    snapped_rotation: FloatVectorProperty(
        name="Snapped Rotation",
        default=(0, 0, 0),
        subtype='QUATERNION'
    )

    has_hit: BoolProperty(name="has_hit", default=False)
    thumbnail_image = StringProperty(
        name="Thumbnail Image",
        description="",
        default=paths.get_addon_thumbnail_path('thumbnail_notready.jpg'),
    )


def get_render_asset_name(self):
    props = utils.get_upload_props()
    if props is not None:
        return props.name
    return ''


def get_render_engine(self):
    return 0


class Hana3DRenderProps(PropertyGroup):
    user_id: IntProperty(name="User ID", description="", default=0)
    balance: StringProperty(name="Credits", description="", default="$0.00")
    asset: StringProperty(name="Asset", description="", get=get_render_asset_name)
    engine: EnumProperty(
        name="Engine",
        items=(
             ("CYCLES", "Cycles", ""),
             ("BLENDER_EEVEE", "Eevee", "")
        ),
        description="",
        get=get_render_engine  # TODO: Remove getter when both available at notRenderFarm
    )
    frame_animation: EnumProperty(
        name="Frame vs Animation",
        items=(
            ("FRAME", "Single Frame", "", "RENDER_STILL", 0),
            ("ANIMATION", "Animation", "", "RENDER_ANIMATION", 1),
        ),
        description="",
        default="FRAME",
    )

    render_state: StringProperty(
        name="Render Generating State",
        description="",
        default="Starting Render process"
    )

    rendering: BoolProperty(
        name="Rendering",
        description="True when background process is running",
        default=False
    )

    render_path: StringProperty(
        name="Path to complete render",
        description="",
        default=""
    )


def workspace_items(self, context):
    profile = bpy.context.window_manager.get('hana3d profile')
    if profile is not None:
        user = profile.get('user')
        if user is not None:
            workspaces = tuple(
                (workspace['id'], workspace['name'], '',) for workspace in user['workspaces']
            )
            return workspaces
    return ()


class Hana3DCommonSearchProps(object):
    # STATES
    is_searching: BoolProperty(
        name="Searching",
        description="search is currently running (internal)",
        default=False
    )
    is_downloading: BoolProperty(
        name="Downloading",
        description="download is currently running (internal)",
        default=False
    )
    search_done: BoolProperty(
        name="Search Completed",
        description="at least one search did run (internal)",
        default=False
    )
    public_only: BoolProperty(
        name="Public assets",
        description="Search only for public assets",
        default=False,
        update=search.search_update,
    )
    search_error: BoolProperty(
        name="Search Error",
        description="last search had an error",
        default=False
    )
    report: StringProperty(name="Report", description="errors and messages", default="")

    search_verification_status: EnumProperty(
        name="Verification status",
        description="Search by verification status",
        items=(
            ('ALL', 'All', 'All'),
            ('UPLOADING', 'Uploading', 'Uploading'),
            ('UPLOADED', 'Uploaded', 'Uploaded'),
            ('READY', 'Ready for V.', 'Ready for validation (deprecated since 2.8)'),
            ('VALIDATED', 'Validated', 'Calidated'),
            ('ON_HOLD', 'On Hold', 'On Hold'),
            ('REJECTED', 'Rejected', 'Rejected'),
            ('DELETED', 'Deleted', 'Deleted'),
        ),
        default='ALL',
    )

    workspace: EnumProperty(
        items=workspace_items,
        name='User workspaces',
        description='User option to choose between workspaces',
        default=None,
        options={'ANIMATABLE'},
    )


def name_update(self, context):
    ''' checks for name change, because it decides if whole asset has to be re-uploaded.
     Name is stored in the blend file and that's the reason.'''
    utils.name_update()


def update_tags(self, context):
    props = utils.get_upload_props()

    commasep = props.tags.split(',')
    ntags = []
    for tag in commasep:
        if len(tag) > 19:
            short_tags = tag.split(' ')
            for short_tag in short_tags:
                if len(short_tag) > 19:
                    short_tag = short_tag[:18]
                ntags.append(short_tag)
        else:
            ntags.append(tag)
    if len(ntags) == 1:
        ntags = ntags[0].split(' ')
    ns = ''
    for t in ntags:
        if t != '':
            ns += t + ','
    ns = ns[:-1]
    if props.tags != ns:
        props.tags = ns


class Hana3DCommonUploadProps(object):
    id: StringProperty(
        name="Asset Version Id",
        description="Unique name of the asset version(hidden)",
        default=""
    )
    asset_base_id: StringProperty(
        name="Asset Base Id",
        description="Unique name of the asset (hidden)",
        default="",
    )
    name: StringProperty(
        name="Name",
        description="Main name of the asset",
        default="",
        update=name_update
    )
    # this is to store name for purpose of checking if name has changed.
    name_old: StringProperty(
        name="Old Name",
        description="Old name of the asset",
        default="",
    )

    description: StringProperty(
        name="Description",
        description="Description of the asset",
        default=""
    )
    tags: StringProperty(
        name="Tags",
        description="List of tags, separated by commas (optional)",
        default="",
        update=update_tags,
    )

    name_changed: BoolProperty(
        name="Name Changed",
        description="Name has changed, the asset has to be re-uploaded with all data",
        default=False,
    )

    is_public: BoolProperty(
        name="Public asset",
        description="Upload asset as public",
        default=False
    )

    uploading: BoolProperty(
        name="Uploading",
        description="True when background process is running",
        default=False,
        update=autothumb.update_upload_material_preview,
    )
    upload_state: StringProperty(
        name="State Of Upload",
        description="bg process reports for upload",
        default=''
    )

    has_thumbnail: BoolProperty(
        name="Has Thumbnail",
        description="True when thumbnail was checked and loaded",
        default=False,
    )

    thumbnail_generating_state: StringProperty(
        name="Thumbnail Generating State",
        description="bg process reports for thumbnail generation",
        default='Please add thumbnail(jpg, at least 512x512)',
    )

    report: StringProperty(
        name="Missing Upload Properties",
        description="used to write down what's missing",
        default='',
    )

    workspace: EnumProperty(
        items=workspace_items,
        name='User workspaces',
        description='User option to choose between workspaces',
        default=None,
        options={'ANIMATABLE'},
    )

    publish_message: StringProperty(
        name="Publish Message",
        description="Changes from previous version",
        default=""
    )


class Hana3DMaterialSearchProps(PropertyGroup, Hana3DCommonSearchProps):
    search_keywords: StringProperty(
        name="Search",
        description="Search for these keywords",
        default="",
        update=search.search_update,
    )

    automap: BoolProperty(
        name="Auto-Map",
        description="reset object texture space and also add automatically a cube mapped UV "
        "to the object. \n this allows most materials to apply instantly to any mesh",
        default=False,
    )


class Hana3DMaterialUploadProps(PropertyGroup, Hana3DCommonUploadProps):
    # TODO remove when removing addon thumbnailer
    texture_size_meters: FloatProperty(
        name="Texture Size in Meters",
        description="face count, autofilled",
        default=1.0,
        min=0
    )

    thumbnail_scale: FloatProperty(
        name="Thumbnail Object Size",
        description="size of material preview object in meters "
        "- change for materials that look better at sizes different than 1m",
        default=1,
        min=0.00001,
        max=10,
    )
    thumbnail_background: BoolProperty(
        name="Thumbnail Background (for Glass only)",
        description="For refractive materials, you might need a background. "
        "Don't use if thumbnail looks good without it!",
        default=False,
    )
    thumbnail_background_lightness: FloatProperty(
        name="Thumbnail Background Lightness",
        description="set to make your material stand out",
        default=0.9,
        min=0.00001,
        max=1,
    )
    thumbnail_samples: IntProperty(
        name="Cycles Samples",
        description="cycles samples setting",
        default=150,
        min=5,
        max=5000
    )
    thumbnail_denoising: BoolProperty(
        name="Use Denoising",
        description="Use denoising",
        default=True
    )
    adaptive_subdivision: BoolProperty(
        name="Adaptive Subdivide",
        description="Use adaptive displacement subdivision",
        default=False,
    )

    thumbnail_resolution: EnumProperty(
        name="Resolution",
        items=thumbnail_resolutions,
        description="Thumbnail resolution.",
        default="512",
    )

    thumbnail_generator_type: EnumProperty(
        name="Thumbnail Style",
        items=(
            ('BALL', 'Ball', ""),
            ('CUBE', 'Cube', 'cube'),
            ('FLUID', 'Fluid', 'Fluid'),
            ('CLOTH', 'Cloth', 'Cloth'),
            ('HAIR', 'Hair', 'Hair  '),
        ),
        description="Style of asset",
        default="BALL",
    )

    thumbnail: StringProperty(
        name="Thumbnail",
        description="Path to the thumbnail - 512x512 .jpg image",
        subtype='FILE_PATH',
        default="",
        update=autothumb.update_upload_material_preview,
    )

    is_generating_thumbnail: BoolProperty(
        name="Generating Thumbnail",
        description="True when background process is running",
        default=False,
        update=autothumb.update_upload_material_preview,
    )

    client: StringProperty(name="Client")
    sku: StringProperty(name="SKU")
    custom_props: PointerProperty(type=custom_props.CustomPropsPropertyGroup)


# upload properties
class Hana3DModelUploadProps(PropertyGroup, Hana3DCommonUploadProps):
    manufacturer: StringProperty(
        name="Manufacturer",
        description="Manufacturer, company making a design peace or product. Not you",
        default="",
    )
    designer: StringProperty(
        name="Designer",
        description="Author of the original design piece depicted. Usually not you",
        default="",
    )

    thumbnail: StringProperty(
        name="Thumbnail",
        description="Path to the thumbnail - 512x512 .jpg image",
        subtype='FILE_PATH',
        default="",
        update=autothumb.update_upload_model_preview,
    )

    thumbnail_background_lightness: FloatProperty(
        name="Thumbnail Background Lightness",
        description="set to make your material stand out",
        default=0.9,
        min=0.01,
        max=10,
    )

    thumbnail_angle: EnumProperty(
        name='Thumbnail Angle',
        items=thumbnail_angles,
        default='DEFAULT',
        description='thumbnailer angle',
    )

    thumbnail_snap_to: EnumProperty(
        name='Model Snaps To:',
        items=thumbnail_snap,
        default='GROUND',
        description='typical placing of the interior.'
        'Leave on ground for most objects that respect gravity :)',
    )

    thumbnail_resolution: EnumProperty(
        name="Resolution",
        items=thumbnail_resolutions,
        description="Thumbnail resolution.",
        default="512",
    )

    thumbnail_samples: IntProperty(
        name="Cycles Samples",
        description="cycles samples setting",
        default=200,
        min=5,
        max=5000
    )
    thumbnail_denoising: BoolProperty(
        name="Use Denoising",
        description="Use denoising",
        default=True
    )

    dimensions: FloatVectorProperty(
        name="Dimensions",
        description="dimensions of the whole asset hierarchy",
        default=(0, 0, 0),
    )
    bbox_min: FloatVectorProperty(
        name="Bbox Min",
        description="dimensions of the whole asset hierarchy",
        default=(-0.25, -0.25, 0),
    )
    bbox_max: FloatVectorProperty(
        name="Bbox Max",
        description="dimensions of the whole asset hierarchy",
        default=(0.25, 0.25, 0.5),
    )

    face_count: IntProperty(name="Face count", description="face count, autofilled", default=0)
    face_count_render: IntProperty(
        name="Render Face Count",
        description="render face count, autofilled",
        default=0
    )

    object_count: IntProperty(
        name="Number of Objects",
        description="how many objects are in the asset, autofilled",
        default=0,
    )

    # THUMBNAIL STATES
    is_generating_thumbnail: BoolProperty(
        name="Generating Thumbnail",
        description="True when background process is running",
        default=False,
        update=autothumb.update_upload_model_preview,
    )

    has_autotags: BoolProperty(
        name="Has Autotagging Done",
        description="True when autotagging done",
        default=False
    )

    client: StringProperty(name="Client")
    sku: StringProperty(name="SKU")
    custom_props: PointerProperty(type=custom_props.CustomPropsPropertyGroup)


class Hana3DSceneUploadProps(PropertyGroup, Hana3DCommonUploadProps):
    thumbnail: StringProperty(
        name="Thumbnail",
        description="Path to the thumbnail - 512x512 .jpg image",
        subtype='FILE_PATH',
        default="",
        update=autothumb.update_upload_scene_preview,
    )

    dimensions: FloatVectorProperty(
        name="Dimensions",
        description="dimensions of the whole asset hierarchy",
        default=(0, 0, 0),
    )
    bbox_min: FloatVectorProperty(
        name="Dimensions",
        description="dimensions of the whole asset hierarchy",
        default=(-0.25, -0.25, 0),
    )
    bbox_max: FloatVectorProperty(
        name="Dimensions",
        description="dimensions of the whole asset hierarchy",
        default=(0.25, 0.25, 0.5),
    )

    face_count: IntProperty(name="Face Count", description="face count, autofilled", default=0)
    face_count_render: IntProperty(
        name="Render Face Count",
        description="render face count, autofilled",
        default=0
    )

    object_count: IntProperty(
        name="Number of Objects",
        description="how many objects are in the asset, autofilled",
        default=0,
    )

    # THUMBNAIL STATES
    is_generating_thumbnail: BoolProperty(
        name="Generating Thumbnail",
        description="True when background process is running",
        default=False,
        update=autothumb.update_upload_scene_preview,
    )

    has_autotags: BoolProperty(
        name="Has Autotagging Done",
        description="True when autotagging done",
        default=False
    )

    thumbnail_denoising: BoolProperty(
        name="Use Denoising",
        description="Use denoising",
        default=True
    )
    thumbnail_resolution: EnumProperty(
        name="Resolution",
        items=thumbnail_resolutions,
        description="Thumbnail resolution.",
        default="512",
    )
    thumbnail_samples: IntProperty(
        name="Cycles Samples",
        description="cycles samples setting",
        default=200,
        min=5,
        max=5000
    )


class Hana3DModelSearchProps(PropertyGroup, Hana3DCommonSearchProps):
    search_keywords: StringProperty(
        name="Search",
        description="Search for these keywords",
        default="",
        update=search.search_update,
    )

    append_method: EnumProperty(
        name="Import Method",
        items=(
            ('LINK_COLLECTION', 'Link', 'Link Collection'),
            ('APPEND_OBJECTS', 'Append', 'Append as Objects'),
        ),
        description="Appended objects are editable in your scene."
        "Linked assets are saved in original files, "
        "aren't editable but also don't increase your file size",
        default="APPEND_OBJECTS",
    )
    append_link: EnumProperty(
        name="How to Attach",
        items=(('LINK', 'Link', ''), ('APPEND', 'Append', ''),),
        description="choose if the assets will be linked or appended",
        default="APPEND",
    )
    import_as: EnumProperty(
        name="Import as",
        items=(('GROUP', 'group', ''), ('INDIVIDUAL', 'objects', ''),),
        description="choose if the assets will be linked or appended",
        default="GROUP",
    )
    offset_rotation_amount: FloatProperty(
        name="Offset Rotation",
        description="offset rotation, hidden prop",
        default=0,
        min=0,
        max=360,
        subtype='ANGLE',
    )
    offset_rotation_step: FloatProperty(
        name="Offset Rotation Step",
        description="offset rotation, hidden prop",
        default=math.pi / 2,
        min=0,
        max=180,
        subtype='ANGLE',
    )


class Hana3DSceneSearchProps(PropertyGroup, Hana3DCommonSearchProps):
    search_keywords: StringProperty(
        name="Search",
        description="Search for these keywords",
        default="",
        update=search.search_update,
    )
    merge_add: EnumProperty(
        name="How to Attach Scene",
        items=(('MERGE', 'Merge Scenes', ''), ('ADD', 'Add New Scene', ''),),
        description="choose if the scene will be merged or appended",
        default="MERGE",
    )
    import_world: BoolProperty(
        name='Import World',
        description="import world data to current scene",
        default=True
    )
    import_render: BoolProperty(
        name='Import Render Settings',
        description="import render settings to current scene",
        default=True,
    )


@addon_updater_ops.make_annotations
class Hana3DAddonPreferences(AddonPreferences):
    # this must match the addon name, use '__package__'
    # when defining this in a submodule of a python package.
    bl_idname = __name__

    default_global_dict = paths.default_global_dict()

    api_key: StringProperty(
        name="Hana3D API Key",
        description="Your Hana3D API Key. Get it from your page on the website",
        default="",
        subtype="PASSWORD",
        update=utils.save_prefs,
    )

    api_key_refresh: StringProperty(
        name="hana3d refresh API Key",
        description="API key used to refresh the token regularly.",
        default="",
        subtype="PASSWORD",
    )

    api_key_timeout: IntProperty(
        name='api key timeout',
        description='time where the api key will need to be refreshed',
        default=0,
        update=utils.save_prefs,
    )

    api_key_life: IntProperty(
        name='api key life time',
        description='maximum lifetime of the api key, in seconds',
        default=3600,
        update=utils.save_prefs,
    )

    refresh_in_progress: BoolProperty(
        name="Api key refresh in progress",
        description="Api key is currently being refreshed. Don't refresh it again.",
        default=False,
    )

    login_attempt: BoolProperty(
        name="Login/Signup attempt",
        description="When this is on, hana3d is trying to connect and login",
        default=False,
    )

    show_on_start: BoolProperty(
        name="Show assetbar when starting blender",
        description="Show assetbar when starting blender",
        default=False,
    )

    search_in_header: BoolProperty(
        name="Show 3D view header",
        description="Show 3D view header",
        default=True
    )

    global_dir: StringProperty(
        name="Global Files Directory",
        description="Global storage for your assets, will use subdirectories for the contents",
        subtype='DIR_PATH',
        default=default_global_dict,
        update=utils.save_prefs,
    )

    project_subdir: StringProperty(
        name="Project Assets Subdirectory",
        description="where data will be stored for individual projects",
        subtype='DIR_PATH',
        default="//assets",
    )

    directory_behaviour: EnumProperty(
        name="Use Directories",
        items=(
            (
                'BOTH',
                'Global and subdir',
                'store files both in global lib and subdirectory of current project. '
                'Warning - each file can be many times on your harddrive, '
                'but helps you keep your projects in one piece',
            ),
            (
                'GLOBAL',
                'Global',
                "store downloaded files only in global directory. \n "
                "This can bring problems when moving your projects, \n"
                "since assets won't be in subdirectory of current project",
            ),
            (
                'LOCAL',
                'Local',
                'store downloaded files only in local directory.\n'
                ' This can use more bandwidth when you reuse assets in different projects. ',
            ),
        ),
        description="Which directories will be used for storing downloaded data",
        default="BOTH",
    )
    thumbnail_use_gpu: BoolProperty(
        name="Use GPU for Thumbnails Rendering",
        description="By default this is off so you can continue your work without any lag",
        default=False,
    )

    max_assetbar_rows: IntProperty(
        name="Max Assetbar Rows",
        description="max rows of assetbar in the 3D view",
        default=1,
        min=0,
        max=20,
    )

    thumb_size: IntProperty(name="Assetbar thumbnail Size", default=96, min=-1, max=256)

    asset_counter: IntProperty(
        name="Usage Counter",
        description="Counts usages so it asks for registration only after reaching a limit",
        default=0,
        min=0,
        max=20000,
    )

    first_run: BoolProperty(
        name="First run",
        description="Detects if addon was already registered/run.",
        default=True,
        update=utils.save_prefs,
    )

    auto_check_update = bpy.props.BoolProperty(
        name="Auto-check for Update",
        description="If enabled, auto-check for updates using an interval",
        default=False,
    )
    updater_intrval_months = bpy.props.IntProperty(
        name='Months',
        description="Number of months between checking for updates",
        default=0,
        min=0
    )
    updater_intrval_days = bpy.props.IntProperty(
        name='Days',
        description="Number of days between checking for updates",
        default=7,
        min=0,
        max=31,
    )
    updater_intrval_hours = bpy.props.IntProperty(
        name='Hours',
        description="Number of hours between checking for updates",
        default=0,
        min=0,
        max=23,
    )
    updater_intrval_minutes = bpy.props.IntProperty(
        name='Minutes',
        description="Number of minutes between checking for updates",
        default=0,
        min=0,
        max=59,
    )

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "show_on_start")

        if self.api_key.strip() == '':
            ui_panels.draw_login_buttons(layout)
        else:
            layout.operator("wm.hana3d_logout", text="Logout", icon='URL')

        layout.prop(self, "api_key", text='Your API Key')
        layout.prop(self, "global_dir")
        layout.prop(self, "project_subdir")
        # layout.prop(self, "temp_dir")
        layout.prop(self, "directory_behaviour")
        layout.prop(self, "thumbnail_use_gpu")
        layout.prop(self, "thumb_size")
        layout.prop(self, "max_assetbar_rows")
        layout.prop(self, "search_in_header")

        addon_updater_ops.update_settings_ui(self, context)


# registration
classes = (
    Hana3DAddonPreferences,
    Hana3DUIProps,
    Hana3DRenderProps,
    Hana3DModelSearchProps,
    Hana3DModelUploadProps,
    Hana3DSceneSearchProps,
    Hana3DSceneUploadProps,
    Hana3DMaterialUploadProps,
    Hana3DMaterialSearchProps,
)


def register():
    addon_updater_ops.register(bl_info)

    custom_props.register_custom_props()

    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Scene.Hana3DUI = PointerProperty(type=Hana3DUIProps)
    bpy.types.Scene.Hana3DRender = PointerProperty(type=Hana3DRenderProps)

    # MODELS
    bpy.types.Scene.hana3d_models = PointerProperty(type=Hana3DModelSearchProps)
    bpy.types.Object.hana3d = PointerProperty(type=Hana3DModelUploadProps)

    # SCENES
    bpy.types.Scene.hana3d_scene = PointerProperty(type=Hana3DSceneSearchProps)
    bpy.types.Scene.hana3d = PointerProperty(type=Hana3DSceneUploadProps)

    # MATERIALS
    bpy.types.Scene.hana3d_mat = PointerProperty(type=Hana3DMaterialSearchProps)
    bpy.types.Material.hana3d = PointerProperty(type=Hana3DMaterialUploadProps)

    search.register_search()
    asset_inspector.register_asset_inspector()
    download.register_download()
    upload.register_upload()
    autothumb.register_thumbnailer()
    ui.register_ui()
    icons.register_icons()
    ui_panels.register_ui_panels()
    bg_blender.register()
    utils.load_prefs()
    hana3d_oauth.register()
    tasks_queue.register()
    render_ops.register()

    bpy.app.timers.register(check_timers_timer, persistent=True)

    bpy.app.handlers.load_post.append(scene_load)


def unregister():
    addon_updater_ops.unregister()

    bpy.app.timers.unregister(check_timers_timer)
    ui_panels.unregister_ui_panels()
    ui.unregister_ui()

    icons.unregister_icons()
    search.unregister_search()
    asset_inspector.unregister_asset_inspector()
    download.unregister_download()
    upload.unregister_upload()
    autothumb.unregister_thumbnailer()
    bg_blender.unregister()
    hana3d_oauth.unregister()
    tasks_queue.unregister()
    render_ops.unregister()

    del bpy.types.Scene.hana3d_models
    del bpy.types.Scene.hana3d_scene
    del bpy.types.Scene.hana3d_mat

    del bpy.types.Scene.hana3d
    del bpy.types.Object.hana3d
    del bpy.types.Material.hana3d

    for cls in classes:
        bpy.utils.unregister_class(cls)

    custom_props.unregister_custom_props()

    bpy.app.handlers.load_post.remove(scene_load)
