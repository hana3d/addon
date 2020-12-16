"""Search/Upload Panel."""
import bpy
from bpy.types import Panel

from ... import utils
from ...config import HANA3D_DESCRIPTION, HANA3D_NAME, HANA3D_UI
from ..search.search import Search
from .lib import draw_assetbar_show_hide


class Hana3DUnifiedPanel(Panel):  # noqa: WPS214
    """Search/Upload Panel."""

    bl_category = HANA3D_DESCRIPTION
    bl_idname = f'VIEW3D_PT_{HANA3D_NAME}_unified'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_label = f'Find and Upload Assets to {HANA3D_DESCRIPTION}'

    @classmethod
    def poll(cls, context):  # noqa: D102
        return True

    def draw(self, context):  # noqa: D102,WPS210,WPS213
        scene = context.scene
        ui_props = getattr(context.window_manager, HANA3D_UI)
        layout = self.layout

        row = layout.row()
        row.prop(ui_props, 'down_up', expand=True, icon_only=False)
        layout.prop(ui_props, 'asset_type', expand=False, text='')

        if ui_props.down_up == 'SEARCH':
            if utils.profile_is_validator():
                search = Search(context)
                search_props = search.props
                layout.prop(search_props, 'search_verification_status')
            if ui_props.asset_type in {'MODEL', 'SCENE', 'MATERIAL'}:
                self._draw_panel_common_search(context)

        elif ui_props.down_up == 'UPLOAD':
            if ui_props.assetbar_on:
                text = 'Hide asset preview - ;'
            else:
                text = 'Show asset preview - ;'
            op = layout.operator(f'view3d.{HANA3D_NAME}_asset_bar', text=text, icon='EXPORT')
            op.keep_running = False
            op.do_search = False
            op.tooltip = 'Show/Hide asset preview'

            engine = scene.render.engine
            if engine not in {'CYCLES', 'BLENDER_EEVEE'}:
                rtext = (
                    'Only Cycles and EEVEE render engines are currently supported. '
                    + f'Please use Cycles for all assets you upload to {HANA3D_DESCRIPTION}.'
                )
                self._label_multiline(rtext, icon='ERROR', width=w)
                return

            if ui_props.asset_type == 'MODEL':
                if bpy.context.view_layer.objects.active is not None:
                    self._draw_panel_common_upload(context)
                else:
                    layout.label(text='selet object to upload')
            elif ui_props.asset_type == 'SCENE':
                self._draw_panel_common_upload(context)
            elif ui_props.asset_type == 'MATERIAL':
                active_object = bpy.context.view_layer.objects.active is not None
                active_material = bpy.context.active_object.active_material is not None
                if active_object and active_material:
                    self._draw_panel_common_upload(context)
                else:
                    self._label_multiline(
                        text='select object with material to upload materials',
                        width=w,
                    )

    def _label_multiline(self, text='', icon='NONE', width=-1):  # noqa: WPS210
        """Draw a ui label, but try to split it in multiple lines.

        Parameters:
            text: Text to be displayed
            icon: Icon to be used
            width: Line width
        """
        if text.strip() == '':
            return
        lines = text.split('\n')
        if width > 0:
            scaling_factor = 5.5
            threshold = int(width / scaling_factor)
        else:
            threshold = 35
        maxlines = 8
        li = 0
        for line in lines:
            while len(line) > threshold:
                index = line.rfind(' ', 0, threshold)
                if index < 1:
                    index = threshold
                l1 = line[:index]
                layout.label(text=l1, icon=icon)
                icon = 'NONE'
                line = line[index:].lstrip()
                li += 1
                if li > maxlines:
                    break
            if li > maxlines:
                break
            self.layout.label(text=line, icon=icon)
            icon = 'NONE'

    def _prop_needed(self, layout, props, name, value, is_not_filled=''):  # noqa: WPS211,WPS110
        row = layout.row()
        if value == is_not_filled:
            row.alert = True
            row.prop(props, name)
            row.alert = False
        else:
            row.prop(props, name)
        return row

    def _draw_selected_tags(self, layout, props, operator):
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

    def _draw_selected_libraries(self, layout, props, operator):
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

    def _draw_panel_common_search(self, context):  # noqa: WPS210,WPS213
        layout = self.layout
        uiprops = getattr(bpy.context.window_manager, HANA3D_UI)
        asset_type = uiprops.asset_type

        search = Search(context)
        search_props = search.props

        row = layout.row()
        row.prop(search_props, 'search_keywords', text='', icon='VIEWZOOM')
        draw_assetbar_show_hide(row)
        layout.prop(search_props, 'workspace', expand=False, text='Workspace')
        row = layout.row()
        row.prop_search(search_props, 'libraries_input', search_props, 'libraries_list', icon='VIEWZOOM')  # noqa: E501
        row.operator(f'object.{HANA3D_NAME}_refresh_libraries', text='', icon='FILE_REFRESH')
        self._draw_selected_libraries(layout, search_props, f'object.{HANA3D_NAME}_remove_library_search')  # noqa: E501
        layout.prop_search(search_props, 'tags_input', search_props, 'tags_list', icon='VIEWZOOM')
        self._draw_selected_tags(layout, search_props, f'object.{HANA3D_NAME}_remove_tag_search')
        layout.prop(search_props, 'public_only')
        self._label_multiline(text=search_props.report)

        if asset_type == 'MODEL':
            layout.separator()
            layout.label(text='Import method:')
            layout.prop(search_props, 'append_method', expand=True, icon_only=False)
            row = layout.row(align=True)
            row.operator(f'scene.{HANA3D_NAME}_batch_download')
        # elif asset_type == 'SCENE':  # TODO uncomment after fixing scene merge  # noqa: E800
        #     layout.separator()  # noqa: E800
        #     layout.label(text='Import method:')  # noqa: E800
        #     layout.prop(props, 'merge_add', expand=True, icon_only=False)  # noqa: E800
        #     if props.merge_add == 'MERGE':  # noqa: E800
        #         layout.prop(props, 'import_world')  # noqa: E800
        #         layout.prop(props, 'import_render')  # noqa: E800
        #         layout.prop(props, 'import_compositing')  # noqa: E800

    def _draw_panel_common_upload(self, context):  # noqa: WPS210,WPS213
        layout = self.layout
        uiprops = getattr(bpy.context.window_manager, HANA3D_UI)
        asset_type = uiprops.asset_type
        props = utils.get_upload_props()

        box = layout.box()
        box.label(text='Workspace and Lib', icon='ASSET_MANAGER')
        box.prop(props, 'workspace', expand=False, text='Workspace')
        row = box.row()
        row.prop_search(props, 'libraries_input', props, 'libraries_list', icon='VIEWZOOM')
        row.operator(f'object.{HANA3D_NAME}_refresh_libraries', text='', icon='FILE_REFRESH')
        self._draw_selected_libraries(box, props, f'object.{HANA3D_NAME}_remove_library_upload')
        for name in props.custom_props.keys():
            box.prop(props.custom_props, f'["{name}"]')

        box = layout.box()
        box.label(text='Asset Info', icon='MESH_CUBE')
        row = self._prop_needed(box, props, 'name', props.name)
        row.operator(f'object.{HANA3D_NAME}_share_asset', text='', icon='LINKED')
        col = box.column()
        if props.is_generating_thumbnail:
            col.enabled = False
        row = col.row(align=True)
        self._prop_needed(row, props, 'thumbnail', props.has_thumbnail, is_not_filled=False)
        if bpy.context.scene.render.engine in {'CYCLES', 'BLENDER_EEVEE'}:
            if asset_type == 'MODEL':
                row.operator(f'object.{HANA3D_NAME}_thumbnail', text='', icon='IMAGE_DATA')
            elif asset_type == 'SCENE':
                row.operator(f'scene.{HANA3D_NAME}_thumbnail', text='', icon='IMAGE_DATA')
            elif asset_type == 'MATERIAL':
                row.operator(f'material.{HANA3D_NAME}_thumbnail', text='', icon='IMAGE_DATA')
        if props.is_generating_thumbnail or props.thumbnail_generating_state != '':
            row = box.row()
            row.label(text=props.thumbnail_generating_state)
            if props.is_generating_thumbnail:
                op = row.operator(f'object.{HANA3D_NAME}_kill_bg_process', text='', icon='CANCEL')
                op.process_source = asset_type
                op.process_type = 'THUMBNAILER'
        box.prop(props, 'description')
        # box.prop(props, 'is_public')  # Commented out until feature is needed  # noqa: E800

        box = layout.box()
        box.label(text='Tags', icon='COLOR')
        row = box.row(align=True)
        row.prop_search(props, 'tags_input', props, 'tags_list', icon='VIEWZOOM')
        op = row.operator(f'object.{HANA3D_NAME}_add_tag', text='', icon='ADD')
        self._draw_selected_tags(box, props, f'object.{HANA3D_NAME}_remove_tag_upload')

        self._prop_needed(layout, props, 'publish_message', props.publish_message)

        if props.upload_state != '':
            self._label_multiline(text=props.upload_state, width=context.region.width)
        if props.uploading:
            op = layout.operator(f'object.{HANA3D_NAME}_kill_bg_process', text='', icon='CANCEL')
            op.process_source = asset_type
            op.process_type = 'UPLOAD'
            box = box.column()
            box.enabled = False

        row = layout.row()
        row.scale_y = 2.0
        if props.view_id == '' or props.workspace != props.view_workspace:
            optext = f'Upload {asset_type.lower()}'
            op = row.operator(f'object.{HANA3D_NAME}_upload', text=optext, icon='EXPORT')
            op.asset_type = asset_type

        if props.view_id != '' and props.workspace == props.view_workspace:
            op = row.operator(f'object.{HANA3D_NAME}_upload', text='Reupload asset', icon='EXPORT')
            op.asset_type = asset_type
            op.reupload = True

            op = row.operator(
                f'object.{HANA3D_NAME}_upload',
                text='Upload as new asset',
                icon='EXPORT',
            )
            op.asset_type = asset_type
            op.reupload = False

            layout.label(text='asset has a version online.')
