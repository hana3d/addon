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
from bpy.types import Panel

from . import (
    download,
    utils,
    addon_updater_ops
)
from .config import HANA3D_NAME


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


def prop_needed(layout, props, name, value, is_not_filled=''):
    row = layout.row()
    if value == is_not_filled:
        row.alert = True
        row.prop(props, name)
        row.alert = False
    else:
        row.prop(props, name)
    return row


def draw_not_logged_in(source):
    title = "User not logged in"

    def draw_message(source, context):
        layout = source.layout
        label_multiline(layout, text='Please login or sign up ' 'to upload files.')
        draw_login_buttons(layout)

    bpy.context.window_manager.popup_menu(draw_message, title=title, icon='INFO')


def draw_selected_tags(layout, props, operator):
    row = layout.row()
    row.scale_y = 0.9
    tag_counter = 0
    for tag in props.tags_list.keys():
        if props.tags_list[tag].selected is True:
            op = row.operator(operator, text=tag, icon='X')
            op.tag = tag
            tag_counter += 1
        if tag_counter == 3:
            row = layout.row()
            row.scale_y = 0.9
            tag_counter = 0


def draw_selected_libraries(layout, props, operator):
    row = layout.row()
    row.scale_y = 0.9
    library_counter = 0
    for library in props.libraries_list.keys():
        if props.libraries_list[library].selected is True:
            op = row.operator(operator, text=library, icon='X')
            op.library = library
            library_counter += 1
        if library_counter == 3:
            row = layout.row()
            row.scale_y = 0.9
            library_counter = 0


def draw_panel_common_upload(layout, context):
    uiprops = bpy.context.window_manager.Hana3DUI
    asset_type = uiprops.asset_type
    props = utils.get_upload_props()

    box = layout.box()
    box.label(text='Workspace and Lib', icon='ASSET_MANAGER')
    box.prop(props, 'workspace', expand=False, text='Workspace')
    row = box.row()
    row.prop_search(props, "libraries_input", props, "libraries_list", icon='VIEWZOOM')
    row.operator('object.hana3d_refresh_libraries', text='', icon='FILE_REFRESH')
    draw_selected_libraries(box, props, "object.hana3d_remove_library_upload")
    for name in props.custom_props.keys():
        box.prop(props.custom_props, f'["{name}"]')

    box = layout.box()
    box.label(text='Asset Info', icon='MESH_CUBE')
    row = prop_needed(box, props, 'name', props.name)
    row.operator('object.hana3d_share_asset', text='', icon='LINKED')
    col = box.column()
    if props.is_generating_thumbnail:
        col.enabled = False
    row = col.row(align=True)
    prop_needed(row, props, 'thumbnail', props.has_thumbnail, False)
    if bpy.context.scene.render.engine in ('CYCLES', 'BLENDER_EEVEE'):
        if asset_type == 'MODEL':
            row.operator('object.hana3d_thumbnail', text='', icon='IMAGE_DATA')
        elif asset_type == 'SCENE':
            row.operator('scene.hana3d_thumbnail', text='', icon='IMAGE_DATA')
        elif asset_type == 'MATERIAL':
            row.operator('material.hana3d_thumbnail', text='', icon='IMAGE_DATA')
    if props.is_generating_thumbnail or props.thumbnail_generating_state != '':
        row = box.row()
        row.label(text=props.thumbnail_generating_state)
        if props.is_generating_thumbnail:
            op = row.operator('object.kill_bg_process', text="", icon='CANCEL')
            op.process_source = asset_type
            op.process_type = 'THUMBNAILER'
    box.prop(props, 'description')
    # box.prop(props, 'is_public')  # Commented out until feature is needed

    box = layout.box()
    box.label(text='Tags', icon='COLOR')
    row = box.row(align=True)
    row.prop_search(props, "tags_input", props, "tags_list", icon='VIEWZOOM')
    op = row.operator('object.hana3d_add_tag', text='', icon='ADD')
    draw_selected_tags(box, props, "object.hana3d_remove_tag_upload")

    prop_needed(layout, props, 'publish_message', props.publish_message)

    if props.upload_state != '':
        label_multiline(layout, text=props.upload_state, width=context.region.width)
    if props.uploading:
        op = layout.operator('object.kill_bg_process', text="", icon='CANCEL')
        op.process_source = asset_type
        op.process_type = 'UPLOAD'
        box = box.column()
        box.enabled = False

    row = layout.row()
    row.scale_y = 2.0
    if props.view_id == '' or props.workspace != props.view_workspace:
        optext = 'Upload %s' % asset_type.lower()
        op = row.operator("object.hana3d_upload", text=optext, icon='EXPORT')
        op.asset_type = asset_type

    if props.view_id != '' and props.workspace == props.view_workspace:
        op = row.operator("object.hana3d_upload", text='Reupload asset', icon='EXPORT')
        op.asset_type = asset_type
        op.reupload = True

        op = row.operator("object.hana3d_upload", text='Upload as new asset', icon='EXPORT')
        op.asset_type = asset_type
        op.reupload = False

        layout.label(text='asset has a version online.')


def draw_panel_common_search(layout, context):
    uiprops = bpy.context.window_manager.Hana3DUI
    asset_type = uiprops.asset_type
    props = utils.get_search_props()

    row = layout.row()
    row.prop(props, "search_keywords", text="", icon='VIEWZOOM')
    draw_assetbar_show_hide(row, props)
    layout.prop(props, 'workspace', expand=False, text='Workspace')
    row = layout.row()
    row.prop_search(props, "libraries_input", props, "libraries_list", icon='VIEWZOOM')
    row.operator('object.hana3d_refresh_libraries', text='', icon='FILE_REFRESH')
    draw_selected_libraries(layout, props, "object.hana3d_remove_library_search")
    layout.prop_search(props, "tags_input", props, "tags_list", icon='VIEWZOOM')
    draw_selected_tags(layout, props, "object.hana3d_remove_tag_search")
    layout.prop(props, "public_only")
    label_multiline(layout, text=props.report)

    if asset_type == 'MODEL':
        layout.separator()
        layout.label(text='Import method:')
        layout.prop(props, 'append_method', expand=True, icon_only=False)
        row = layout.row(align=True)
        op = row.operator("scene.hana3d_batch_download", text='Import first 20')
        op.reset = True
        batch_size = op.batch_size
        op = row.operator("scene.hana3d_batch_download", text=f'Import next {batch_size}')
        op.reset = False
    # elif asset_type == 'SCENE':  # TODO uncomment after fixing scene merge
    #     layout.separator()
    #     layout.label(text='Import method:')
    #     layout.prop(props, 'merge_add', expand=True, icon_only=False)
    #     if props.merge_add == 'MERGE':
    #         layout.prop(props, 'import_world')
    #         layout.prop(props, 'import_render')
    #         layout.prop(props, 'import_compositing')


def draw_assetbar_show_hide(layout, props):
    wm = bpy.context.window_manager
    ui_props = wm.Hana3DUI

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
        user_preferences = bpy.context.preferences.addons[HANA3D_NAME].preferences

        if user_preferences.login_attempt:
            draw_login_progress(layout)
            return

        draw_login_buttons(layout)


def draw_login_progress(layout):
    layout.label(text='Login through browser')
    layout.label(text='in progress.')
    layout.operator("wm.hana3d_login_cancel", text="Cancel", icon='CANCEL')


def draw_login_buttons(layout):
    user_preferences = bpy.context.preferences.addons[HANA3D_NAME].preferences

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
        return True

    def draw(self, context):
        s = context.scene
        wm = context.window_manager
        ui_props = wm.Hana3DUI
        user_preferences = bpy.context.preferences.addons[HANA3D_NAME].preferences
        layout = self.layout

        row = layout.row()
        row.prop(ui_props, 'down_up', expand=True, icon_only=False)
        layout.prop(ui_props, 'asset_type', expand=False, text='')

        w = context.region.width
        if user_preferences.login_attempt:
            draw_login_progress(layout)
            return

        if len(user_preferences.api_key) < 20 and user_preferences.asset_counter > 20:
            draw_login_buttons(layout)
            layout.separator()

        if ui_props.down_up == 'SEARCH':
            if utils.profile_is_validator():
                search_props = utils.get_search_props()
                layout.prop(search_props, 'search_verification_status')
            if ui_props.asset_type == 'MODEL':
                draw_panel_common_search(self.layout, context)
            elif ui_props.asset_type == 'SCENE':
                draw_panel_common_search(self.layout, context)
            elif ui_props.asset_type == 'MATERIAL':
                draw_panel_common_search(self.layout, context)

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
                    draw_panel_common_upload(self.layout, context)
                else:
                    layout.label(text='selet object to upload')
            elif ui_props.asset_type == 'SCENE':
                draw_panel_common_upload(self.layout, context)
            elif ui_props.asset_type == 'MATERIAL':
                if (
                    bpy.context.view_layer.objects.active is not None
                    and bpy.context.active_object.active_material is not None
                ):
                    draw_panel_common_upload(self.layout, context)
                else:
                    label_multiline(
                        layout,
                        text='select object with material to upload materials',
                        width=w
                    )


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
        for view_id, thread in download.download_threads.items():
            row = layout.row()
            row.label(text=thread.asset_data['name'])
            row.label(text=str(int(thread.tcom.progress)) + ' %')
            op = row.operator('scene.hana3d_download_kill', text='', icon='CANCEL')
            op.view_id = view_id


def header_search_draw(self, context):
    '''Top bar menu in 3d view'''

    if not utils.guard_from_crash():
        return

    preferences = context.preferences.addons[HANA3D_NAME].preferences
    if preferences.search_in_header:
        layout = self.layout
        wm = context.window_manager
        ui_props = wm.Hana3DUI
        if ui_props.asset_type == 'MODEL':
            props = wm.hana3d_models
        if ui_props.asset_type == 'MATERIAL':
            props = wm.hana3d_mat
        if ui_props.asset_type == 'SCENE':
            props = wm.hana3d_scene
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

        layout.prop(context.preferences.addons[HANA3D_NAME].preferences, 'search_in_header')


class VIEW3D_PT_hana3d_RenderPanel(Panel):
    """Render Farm operations panel"""

    bl_label = "Manage renders"
    bl_idname = "VIEW3D_PT_hana3d_RenderPanel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Hana3D"

    @classmethod
    def poll(cls, context):
        return True

    def draw(self, context):
        render_props = context.window_manager.Hana3DRender
        asset_props = utils.get_upload_props()
        ui_props = context.window_manager.Hana3DUI

        self.layout.prop(ui_props, 'asset_type_render', expand=False, text='')

        if asset_props is None:
            row = self.layout.row()
            row.label(text='Select an asset')
            return

        self.draw_asset_name(ui_props, render_props)
        self.layout.separator()

        if asset_props.view_id == '':
            row = self.layout.row()
            row.label(text='Upload asset first')
            return

        self.draw_main_panel(render_props, asset_props)
        self.layout.separator()

        self.layout.prop(render_props, 'render_ui_mode', expand=True, icon_only=False)
        self.layout.separator()

        if render_props.render_ui_mode == 'GENERATE':
            self.draw_generate_panel(context, render_props, asset_props)
        elif render_props.render_ui_mode == 'UPLOAD':
            self.draw_upload_panel(asset_props)

    def draw_asset_name(self, ui_props, render_props):
        if ui_props.asset_type == 'MODEL':
            icon = 'OBJECT_DATAMODE'
        elif ui_props.asset_type == 'SCENE':
            icon = 'SCENE_DATA'
        elif ui_props.asset_type == 'MATERIAL':
            icon = 'MATERIAL'
        row = self.layout.row()
        row.prop(render_props, 'asset', text='Asset', icon=icon)

    def draw_main_panel(self, render_props, asset_props):
        if 'jobs' not in asset_props.render_data or len(asset_props.render_data['jobs']) == 0:
            row = self.layout.row()
            row.label(text='This asset has no saved renders in Hana3D')
            return

        box = self.layout.box()
        row = box.row()
        row.prop(asset_props, 'render_job_output', text='Render jobs')
        row = box.row()
        row.template_icon_view(
            asset_props,
            'render_job_output',
            show_labels=True,
            scale=10,
            scale_popup=6,
        )

        row = box.row()
        row.operator('hana3d.import_render', icon='IMPORT')
        row = box.row()
        row.operator('hana3d.remove_render', icon='CANCEL')

    def draw_generate_panel(self, context, render_props, asset_props):
        box = self.layout.box()

        row = box.row()
        row.label(text='Balance')
        row.label(text=render_props.balance)

        box.label(text='Render Parameters', icon='PREFERENCES')
        box.prop(asset_props, 'render_job_name', text='Name')
        box.prop(render_props, 'cameras', expand=False, icon_only=False)
        if render_props.cameras == 'ACTIVE_CAMERA' and context.scene.camera is not None:
            row = box.row()
            row.label(text=context.scene.camera.name_full)
        box.prop(render_props, 'engine')
        row = box.row()
        row.label(text="Resolution X")
        row.prop(context.scene.render, "resolution_x", text='')
        row = box.row()
        row.label(text="Resolution Y")
        row.prop(context.scene.render, "resolution_y", text='')

        row = box.row()
        row.prop(render_props, 'frame_animation', text='')
        if render_props.cameras in ('VISIBLE_CAMERAS', 'ALL_CAMERAS'):
            row.enabled = False
            row = box.row()
            row.label(text="Frame")
            row.prop(context.scene, "frame_current", text='')
            row = box.row()
            row.label(text="Atenção! Só será renderizado um frame por câmera!", icon='ERROR')
        elif render_props.frame_animation == 'FRAME':
            row = box.row()
            row.label(text="Frame")
            row.prop(context.scene, "frame_current", text='')
        elif render_props.frame_animation == 'ANIMATION':
            row = box.row()
            row.label(text="Frame Start")
            row.prop(context.scene, "frame_start", text='')
            row = box.row()
            row.label(text="Frame End")
            row.prop(context.scene, "frame_end", text='')

        if asset_props is not None and asset_props.rendering:
            self.draw_kill_job(asset_props)

        visible_cameras = [ob.name_full for ob in context.scene.objects
                           if ob.type == 'CAMERA' and ob.visible_get()]
        all_cameras = [ob.name_full for ob in context.scene.objects
                       if ob.type == 'CAMERA']
        if render_props.cameras == 'ACTIVE_CAMERA' and context.scene.camera is not None or \
                render_props.cameras == 'VISIBLE_CAMERAS' and len(visible_cameras) or \
                render_props.cameras == 'ALL_CAMERAS' and len(all_cameras):
            row = self.layout.row()
            row.scale_y = 2.0
            row.operator('hana3d.render_scene', icon='SCENE')

    def draw_kill_job(self, asset_props):
        row = self.layout.row(align=True)
        row.label(text=asset_props.render_state)
        op = row.operator('hana3d.cancel_render_job', text="", icon='CANCEL')
        op.view_id = asset_props.view_id

    def draw_upload_panel(self, asset_props):
        box = self.layout.box()

        row = box.row()
        row.prop(asset_props, 'active_image', text='')
        row.operator('hana3d.open_image', text='', icon='FILEBROWSER')

        row = box.row()
        row.prop(asset_props, 'render_job_name', text='Name')
        row = box.row()
        row.label(text=asset_props.upload_render_state)
        row = box.row()
        row.operator('hana3d.upload_render_image', icon='EXPORT')

        # Only work in EDIT_IMAGE space
        # box = self.layout.box()
        # row = box.row()
        # row.template_ID(bpy.context.space_data, 'image', open='image.open')


classes = (
    VIEW3D_PT_UpdaterPanel,
    VIEW3D_PT_hana3d_login,
    VIEW3D_PT_hana3d_unified,
    VIEW3D_PT_hana3d_downloads,
    VIEW3D_PT_hana3d_RenderPanel
)


def register():
    addon_updater_ops.make_annotations(VIEW3D_PT_UpdaterPanel)
    for c in classes:
        bpy.utils.register_class(c)
    bpy.types.VIEW3D_MT_editor_menus.append(header_search_draw)


def unregister():
    for c in reversed(classes):
        bpy.utils.unregister_class(c)
    bpy.types.VIEW3D_MT_editor_menus.remove(header_search_draw)
