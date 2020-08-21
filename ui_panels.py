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
    import importlib

    paths = importlib.reload(paths)
    utils = importlib.reload(utils)
    download = importlib.reload(download)
else:
    from hana3d import paths, utils, download

import bpy
from bpy.types import Panel, Operator

from . import addon_updater_ops


def label_multiline(layout, text='', icon='NONE', width=-1):
    ''' draw a ui label, but try to split it in multiple lines.'''
    if text.strip() == '':
        return
    lines = text.split('\n')
    if width > 0:
        threshold = int(width / 5.5)
    else:
        threshold = 35
    maxlines = 8
    li = 0
    for line in lines:
        while len(line) > threshold:
            i = line.rfind(' ', 0, threshold)
            if i < 1:
                i = threshold
            l1 = line[:i]
            layout.label(text=l1, icon=icon)
            icon = 'NONE'
            line = line[i:].lstrip()
            li += 1
            if li > maxlines:
                break
        if li > maxlines:
            break
        layout.label(text=line, icon=icon)
        icon = 'NONE'


def draw_not_logged_in(source):
    title = "User not logged in"

    def draw_message(source, context):
        layout = source.layout
        label_multiline(layout, text='Please login or sign up ' 'to upload files.')
        draw_login_buttons(layout)

    bpy.context.window_manager.popup_menu(draw_message, title=title, icon='INFO')


def draw_upload_common(layout, context):
    scene = bpy.context.scene
    uiprops = scene.Hana3DUI
    asset_type = uiprops.asset_type
    props = utils.get_upload_props()

    layout.prop(props, 'workspace', expand=False, text='Workspace')
    row = layout.row(align=True)
    col = row.column()
    col.scale_x = 0.7
    col.label(text='Libraries:')
    col = row.column()
    col.scale_x = 1.24
    col.operator(
        "object.hana3d_list_libraries_upload",
        text=props.libraries_text
    )
    for name in props.custom_props.keys():
        layout.prop(props.custom_props, f'["{name}"]')
    prop_needed(layout, props, 'name', props.name)
    layout.prop(props, 'description')
    layout.prop(props, 'publish_message')
    layout.prop(props, 'tags')
    layout.prop(props, 'client')
    layout.prop(props, 'sku')
    layout.prop(props, 'is_public')

    col = layout.column()
    if props.is_generating_thumbnail:
        col.enabled = False
    prop_needed(col, props, 'thumbnail', props.has_thumbnail, False)
    if bpy.context.scene.render.engine in ('CYCLES', 'BLENDER_EEVEE'):
        if asset_type == 'MODEL':
            col.operator(
                "object.hana3d_generate_thumbnail",
                text='Generate thumbnail',
                icon='IMAGE_DATA'
            )
        elif asset_type == 'SCENE':
            col.operator(
                "object.hana3d_scene_thumbnail",
                text='Generate thumbnail',
                icon='IMAGE_DATA'
            )
        elif asset_type == 'MATERIAL':
            col.operator(
                "object.hana3d_material_thumbnail",
                text='Generate thumbnail',
                icon='IMAGE_DATA'
            )
    if props.is_generating_thumbnail:
        row = layout.row(align=True)
        row.label(text=props.thumbnail_generating_state)
        op = row.operator('object.kill_bg_process', text="", icon='CANCEL')
        op.process_source = asset_type
        op.process_type = 'THUMBNAILER'

    if props.upload_state != '':
        label_multiline(layout, text=props.upload_state, width=context.region.width)
    if props.uploading:
        op = layout.operator('object.kill_bg_process', text="", icon='CANCEL')
        op.process_source = asset_type
        op.process_type = 'UPLOAD'
        layout = layout.column()
        layout.enabled = False

    if props.asset_base_id == '':
        optext = 'Upload %s' % asset_type.lower()
        op = layout.operator("object.hana3d_upload", text=optext, icon='EXPORT')
        op.asset_type = asset_type

    if props.asset_base_id != '':
        op = layout.operator("object.hana3d_upload", text='Reupload asset', icon='EXPORT')
        op.asset_type = asset_type
        op.reupload = True

        op = layout.operator("object.hana3d_upload", text='Upload as new asset', icon='EXPORT')
        op.asset_type = asset_type
        op.reupload = False

        layout.label(text='asset has a version online.')


def poll_local_panels():
    user_preferences = bpy.context.preferences.addons['hana3d'].preferences
    return user_preferences.panel_behaviour == 'BOTH' or user_preferences.panel_behaviour == 'LOCAL'


def prop_needed(layout, props, name, value, is_not_filled=''):
    row = layout.row()
    if value == is_not_filled:
        row.alert = True
        row.prop(props, name)
        row.alert = False
    else:
        row.prop(props, name)


def draw_assetbar_show_hide(layout, props):
    s = bpy.context.scene
    ui_props = s.Hana3DUI

    if ui_props.assetbar_on:
        icon = 'HIDE_OFF'
        ttip = 'Click to Hide Asset Bar'
    else:
        icon = 'HIDE_ON'
        ttip = 'Click to Show Asset Bar'
    op = layout.operator('view3d.hana3d_asset_bar', text='', icon=icon)
    op.keep_running = False
    op.do_search = False

    op.tooltip = ttip


def draw_panel_model_search(self, context):
    s = context.scene

    props = s.hana3d_models
    layout = self.layout

    row = layout.row()
    row.prop(props, "search_keywords", text="", icon='VIEWZOOM')
    draw_assetbar_show_hide(row, props)

    # Choose best layout:
    layout.prop(props, 'workspace', expand=False, text='Workspace')
    row = layout.row(align=True)
    col = row.column()
    col.scale_x = 0.7
    col.label(text='Libraries:')
    col = row.column()
    col.scale_x = 1.24
    col.operator(
        "object.hana3d_list_libraries_search",
        text=props.libraries_text
    )

    icon = 'NONE'
    label_multiline(layout, text=props.report, icon=icon)

    layout.prop(props, "public_only")

    # col = layout.column()
    # layout.prop(props, 'append_link', expand=True, icon_only=False)
    # layout.prop(props, 'import_as', expand=True, icon_only=False)

    layout.separator()
    layout.label(text='Import method:')
    row = layout.row()
    row.prop(props, 'append_method', expand=True, icon_only=False)


def draw_panel_scene_search(self, context):
    s = context.scene
    props = s.hana3d_scene
    layout = self.layout

    layout.prop(props, 'workspace', expand=False, text='Workspace')
    row = layout.row(align=True)
    col = row.column()
    col.scale_x = 0.7
    col.label(text='Libraries:')
    col = row.column()
    col.scale_x = 1.24
    col.operator(
        "object.hana3d_list_libraries_search",
        text=props.libraries_text
    )
    layout.prop(props, "public_only")
    layout.prop(props, "search_keywords", text="", icon='VIEWZOOM')
    layout.prop(props, 'merge_add', expand=True, icon_only=False)

    if props.merge_add == 'MERGE':
        layout.prop(props, 'import_world')
        layout.prop(props, 'import_render')


class VIEW3D_PT_hana3d_model_properties(Panel):
    bl_category = "Hana3D"
    bl_idname = "VIEW3D_PT_hana3d_model_properties"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_label = "Selected Model"
    bl_context = "objectmode"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        p = bpy.context.view_layer.objects.active is not None
        return p

    def draw(self, context):
        # draw asset properties here
        layout = self.layout

        o = utils.get_active_model()
        # o = bpy.context.active_object
        if o.get('asset_data') is None:
            label_multiline(
                layout,
                text='To upload this asset to hana3d, go to the Find and Upload Assets panel.',
            )
            layout.prop(o, 'name')

        if o.get('asset_data') is not None:
            ad = o['asset_data']
            layout.label(text=str(ad['name']))
            if o.instance_type == 'COLLECTION' and o.instance_collection is not None:
                layout.operator('object.hana3d_bring_to_scene', text='Bring to scene')


def draw_login_progress(layout):
    layout.label(text='Login through browser')
    layout.label(text='in progress.')
    layout.operator("wm.hana3d_login_cancel", text="Cancel", icon='CANCEL')


class VIEW3D_PT_hana3d_login(Panel):
    bl_category = "Hana3D"
    bl_idname = "VIEW3D_PT_hana3d_login"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_label = "Hana3D Login"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        return True

    def draw(self, context):
        layout = self.layout
        user_preferences = bpy.context.preferences.addons['hana3d'].preferences

        if user_preferences.login_attempt:
            draw_login_progress(layout)
            return

        if user_preferences.enable_oauth:
            draw_login_buttons(layout)


def draw_panel_material_search(self, context):
    wm = context.scene
    props = wm.hana3d_mat

    layout = self.layout
    row = layout.row()
    row.prop(props, "search_keywords", text="", icon='VIEWZOOM')
    draw_assetbar_show_hide(row, props)
    layout.prop(props, 'workspace', expand=False, text='Workspace')
    row = layout.row(align=True)
    col = row.column()
    col.scale_x = 0.7
    col.label(text='Libraries:')
    col = row.column()
    col.scale_x = 1.24
    col.operator(
        "object.hana3d_list_libraries_search",
        text=props.libraries_text
    )
    layout.prop(props, "public_only")
    label_multiline(layout, text=props.report)


def draw_login_buttons(layout):
    user_preferences = bpy.context.preferences.addons['hana3d'].preferences

    if user_preferences.login_attempt:
        draw_login_progress(layout)
    else:
        if user_preferences.api_key == '':
            layout.operator("wm.hana3d_login", text="Login / Sign up", icon='URL')
        else:
            layout.operator("wm.hana3d_logout", text="Logout", icon='URL')


class VIEW3D_PT_hana3d_unified(Panel):
    bl_category = "Hana3D"
    bl_idname = "VIEW3D_PT_hana3d_unified"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_label = "Find and Upload Assets"

    @classmethod
    def poll(cls, context):
        user_preferences = bpy.context.preferences.addons['hana3d'].preferences
        return (
            user_preferences.panel_behaviour == 'BOTH'
            or user_preferences.panel_behaviour == 'UNIFIED'
        )

    def draw(self, context):
        s = context.scene
        ui_props = s.Hana3DUI
        user_preferences = bpy.context.preferences.addons['hana3d'].preferences
        layout = self.layout

        row = layout.row()
        row.prop(ui_props, 'down_up', expand=True, icon_only=False)
        layout.prop(ui_props, 'asset_type', expand=False, text='')

        w = context.region.width
        if user_preferences.login_attempt:
            draw_login_progress(layout)
            return

        if len(user_preferences.api_key) < 20 and user_preferences.asset_counter > 20:
            if user_preferences.enable_oauth:
                draw_login_buttons(layout)
            else:
                op = layout.operator("wm.url_open", text="Get your API Key", icon='QUESTION')
                op.url = paths.HANA3D_SIGNUP_URL
                layout.label(text='Paste your API Key:')
                layout.prop(user_preferences, 'api_key', text='')
            layout.separator()

        if ui_props.down_up == 'SEARCH':
            if utils.profile_is_validator():
                search_props = utils.get_search_props()
                layout.prop(search_props, 'search_verification_status')
            if ui_props.asset_type == 'MODEL':
                draw_panel_model_search(self, context)
            elif ui_props.asset_type == 'SCENE':
                draw_panel_scene_search(self, context)
            elif ui_props.asset_type == 'MATERIAL':
                draw_panel_material_search(self, context)

        elif ui_props.down_up == 'UPLOAD':
            if not ui_props.assetbar_on:
                text = 'Show asset preview - ;'
            else:
                text = 'Hide asset preview - ;'
            op = layout.operator('view3d.hana3d_asset_bar', text=text, icon='EXPORT')
            op.keep_running = False
            op.do_search = False
            op.tooltip = 'Show/Hide asset preview'

            e = s.render.engine
            if e not in ('CYCLES', 'BLENDER_EEVEE'):
                rtext = (
                    'Only Cycles and EEVEE render engines are currently supported. '
                    'Please use Cycles for all assets you upload to hana3d.'
                )
                label_multiline(layout, rtext, icon='ERROR', width=w)
                return

            if ui_props.asset_type == 'MODEL':
                if bpy.context.view_layer.objects.active is not None:
                    draw_upload_common(self.layout, context)
                else:
                    layout.label(text='selet object to upload')
            elif ui_props.asset_type == 'SCENE':
                draw_upload_common(self.layout, context)
            elif ui_props.asset_type == 'MATERIAL':
                if (
                    bpy.context.view_layer.objects.active is not None
                    and bpy.context.active_object.active_material is not None
                ):
                    draw_upload_common(self.layout, context)
                else:
                    label_multiline(
                        layout,
                        text='select object with material to upload materials',
                        width=w
                    )


class OBJECT_MT_hana3d_asset_menu(bpy.types.Menu):
    bl_label = "Asset options:"
    bl_idname = "OBJECT_MT_hana3d_asset_menu"

    def draw(self, context):
        layout = self.layout
        ui_props = context.scene.Hana3DUI

        sr = bpy.context.scene['search results']
        sr = bpy.context.scene['search results orig']['results']
        asset_data = sr[ui_props.active_index]
        author_id = str(asset_data['author']['id'])

        wm = bpy.context.window_manager
        if wm.get('hana3d authors') is not None:
            a = bpy.context.window_manager['hana3d authors'].get(author_id)
            if a is not None:
                # utils.p('author:', a)
                if a.get('aboutMeUrl') is not None:
                    op = layout.operator('wm.url_open', text="Open Author's Website")
                    op.url = a['aboutMeUrl']

                op = layout.operator('view3d.hana3d_search', text="Show Assets By Author")
                op.keywords = ''
                op.author_id = author_id

        op = layout.operator('view3d.hana3d_search', text='Search Similar')
        op.keywords = (
            asset_data['name']
            + ' '
            + asset_data['description']
            + ' '
            + ' '.join(asset_data['tags'])
        )
        if asset_data.get('canDownload') != 0:
            if len(bpy.context.selected_objects) > 0 and ui_props.asset_type == 'MODEL':
                aob = bpy.context.active_object
                if aob is None:
                    aob = bpy.context.selected_objects[0]
                op = layout.operator('scene.hana3d_download', text='Replace Active Models')
                op.asset_type = ui_props.asset_type
                op.asset_index = ui_props.active_index
                op.model_location = aob.location
                op.model_rotation = aob.rotation_euler
                op.target_object = aob.name
                op.material_target_slot = aob.active_material_index
                op.replace = True

        wm = bpy.context.window_manager
        profile = wm.get('hana3d profile')
        if profile is not None:
            # validation
            if utils.profile_is_validator():
                layout.label(text='Validation tools:')
                if asset_data['verificationStatus'] != 'uploaded':
                    op = layout.operator('object.hana3d_change_status', text='set Uploaded')
                    op.asset_id = asset_data['id']
                    op.state = 'uploaded'
                if asset_data['verificationStatus'] != 'validated':
                    op = layout.operator('object.hana3d_change_status', text='Validate')
                    op.asset_id = asset_data['id']
                    op.state = 'validated'
                if asset_data['verificationStatus'] != 'on_hold':
                    op = layout.operator('object.hana3d_change_status', text='Put on Hold')
                    op.asset_id = asset_data['id']
                    op.state = 'on_hold'
                if asset_data['verificationStatus'] != 'rejected':
                    op = layout.operator('object.hana3d_change_status', text='Reject')
                    op.asset_id = asset_data['id']
                    op.state = 'rejected'

            if author_id == str(profile['user']['id']):
                layout.label(text='Management tools:')
                row = layout.row()
                row.operator_context = 'INVOKE_DEFAULT'
                op = row.operator('object.hana3d_change_status', text='Delete')
                op.asset_id = asset_data['id']
                op.state = 'deleted'


class UrlPopupDialog(bpy.types.Operator):
    """Generate Cycles thumbnail for model assets"""

    bl_idname = "wm.hana3d_url_dialog"
    bl_label = "hana3d message:"
    bl_options = {'REGISTER', 'INTERNAL'}

    url: bpy.props.StringProperty(name="Url", description="url", default="")

    link_text: bpy.props.StringProperty(name="Url", description="url", default="Go to website")

    message: bpy.props.StringProperty(name="Text", description="text", default="")

    # @classmethod
    # def poll(cls, context):
    #     return bpy.context.view_layer.objects.active is not None

    def draw(self, context):
        layout = self.layout
        label_multiline(layout, text=self.message)

        layout.active_default = True
        op = layout.operator("wm.url_open", text=self.link_text, icon='QUESTION')
        op.url = self.url

    def execute(self, context):
        # start_thumbnailer(self, context)
        return {'FINISHED'}

    def invoke(self, context, event):
        self.bl_label = 'ahoj'
        wm = context.window_manager

        return wm.invoke_props_dialog(self)


class VIEW3D_PT_hana3d_downloads(Panel):
    bl_category = "Hana3D"
    bl_idname = "VIEW3D_PT_hana3d_downloads"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_label = "Downloads"

    @classmethod
    def poll(cls, context):
        return len(download.download_threads) > 0

    def draw(self, context):
        layout = self.layout
        for threaddata in download.download_threads:
            tcom = threaddata[2]
            asset_data = threaddata[1]
            row = layout.row()
            row.label(text=asset_data['name'])
            row.label(text=str(int(tcom.progress)) + ' %')
            row.operator('scene.hana3d_download_kill', text='', icon='CANCEL')
            if tcom.passargs.get('retry_counter', 0) > 0:
                row = layout.row()
                row.label(text='failed. retrying ... ', icon='ERROR')
                row.label(text=str(tcom.passargs["retry_counter"]))

                layout.separator()


def header_search_draw(self, context):
    '''Top bar menu in 3d view'''

    if not utils.guard_from_crash():
        return

    preferences = bpy.context.preferences.addons['hana3d'].preferences
    if preferences.search_in_header:
        layout = self.layout
        s = bpy.context.scene
        ui_props = s.Hana3DUI
        if ui_props.asset_type == 'MODEL':
            props = s.hana3d_models
        if ui_props.asset_type == 'MATERIAL':
            props = s.hana3d_mat
        if ui_props.asset_type == 'SCENE':
            props = s.hana3d_scene
        # if ui_props.asset_type == 'HDR':
        #     props = s.hana3d_hdr

        if context.space_data.show_region_tool_header is True or context.mode[:4] not in (
            'EDIT',
            'OBJE',
        ):
            layout.separator_spacer()
        layout.prop(ui_props, "asset_type", text='', icon='URL')
        layout.prop(props, "search_keywords", text="", icon='VIEWZOOM')
        draw_assetbar_show_hide(layout, props)


class VIEW3D_PT_UpdaterPanel(Panel):
    """Panel to demo popup notice and ignoring functionality"""

    bl_label = "Preferences"
    bl_idname = "VIEW3D_PT_UpdaterPanel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_context = "objectmode"
    bl_category = "Hana3D"

    def draw(self, context):
        layout = self.layout

        mainrow = layout.row()
        col = mainrow.column()
        addon_updater_ops.update_settings_ui_condensed(self, context, col)

        addon_updater_ops.check_for_update_background()

        addon_updater_ops.update_notice_box_ui(self, context)

        layout.prop(context.preferences.addons['hana3d'].preferences, 'search_in_header')


class ListLibrariesSearch(Operator):
    """Libraries that the view will be assigned to.
If no library is selected the view will be assigned to the default library."""

    bl_idname = "object.hana3d_list_libraries_search"
    bl_label = "Hana3D List Libraries"
    bl_options = {'REGISTER', 'INTERNAL'}

    def draw(self, context):
        props = utils.get_search_props()
        layout = self.layout
        i = 0
        while hasattr(props, f'library_{i}'):
            layout.prop(props, f'library_{i}')
            i += 1

    def execute(self, context):
        return {'INTERFACE'}

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_popup(self)


class ListLibrariesUpload(Operator):
    """Libraries that the view will be assigned to.
If no library is selected the view will be assigned to the default library."""

    bl_idname = "object.hana3d_list_libraries_upload"
    bl_label = "Hana3D List Libraries"
    bl_options = {'REGISTER', 'INTERNAL'}

    def draw(self, context):
        props = utils.get_upload_props()
        layout = self.layout
        i = 0
        while hasattr(props, f'library_{i}'):
            layout.prop(props, f'library_{i}')
            i += 1

    def execute(self, context):
        return {'INTERFACE'}

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_popup(self)


# We can store multiple preview collections here,
# however in this example we only store "main"
preview_collections = {}
classess = (
    VIEW3D_PT_UpdaterPanel,
    VIEW3D_PT_hana3d_login,
    VIEW3D_PT_hana3d_unified,
    VIEW3D_PT_hana3d_model_properties,
    VIEW3D_PT_hana3d_downloads,
    OBJECT_MT_hana3d_asset_menu,
    UrlPopupDialog,
    ListLibrariesSearch,
    ListLibrariesUpload
)


def register_ui_panels():
    addon_updater_ops.make_annotations(VIEW3D_PT_UpdaterPanel)
    for c in classess:
        bpy.utils.register_class(c)
    bpy.types.VIEW3D_MT_editor_menus.append(header_search_draw)


def unregister_ui_panels():
    bpy.types.VIEW3D_MT_editor_menus.remove(header_search_draw)
    for c in classess:
        print('unregister', c)
        bpy.utils.unregister_class(c)
