"""Search Panel."""
import bpy
from bpy.types import Panel

from ... import utils
from ...config import HANA3D_DESCRIPTION, HANA3D_NAME, HANA3D_UI
from ..search import search
from ..unified_props import Unified
from .lib import draw_assetbar_show_hide


class Hana3DSearchPanel(Panel):  # noqa: WPS214
    """Search Panel."""

    bl_category = HANA3D_DESCRIPTION
    bl_idname = f'VIEW3D_PT_{HANA3D_NAME}_search'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_label = f'Find Assets in {HANA3D_DESCRIPTION}'

    @classmethod
    def poll(cls, context):  # noqa: D102
        return True

    def draw(self, context):  # noqa: D102,WPS210,WPS213
        ui_props = getattr(context.window_manager, HANA3D_UI)
        layout = self.layout

        layout.prop(ui_props, 'asset_type_search', expand=False, text='')

        if utils.profile_is_validator():
            search_props = search.get_search_props()
            layout.prop(search_props, 'search_verification_status')
        if ui_props.asset_type_search in {'MODEL', 'SCENE', 'MATERIAL'}:
            self._draw_panel_common_search(context)

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
                self.layout.label(text=l1, icon=icon)
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
        asset_type = uiprops.asset_type_search

        search_props = search.get_search_props()
        unified_props = Unified(context).props

        row = layout.row()
        row.prop(search_props, 'search_keywords', text='', icon='VIEWZOOM')
        draw_assetbar_show_hide(row)
        layout.prop(unified_props, 'workspace', expand=False, text='Workspace')
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
