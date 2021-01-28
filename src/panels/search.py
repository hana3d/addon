"""Search Panel."""
import bpy
from bpy.types import Panel

from ... import utils
from ...config import HANA3D_DESCRIPTION, HANA3D_NAME, HANA3D_UI
from ..search import search
from ..unified_props import Unified
from .lib import (
    draw_assetbar_show_hide,
    draw_selected_libraries,
    draw_selected_tags,
    label_multiline,
)


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
        draw_selected_libraries(layout, search_props, f'object.{HANA3D_NAME}_remove_library_search')  # noqa: E501
        layout.prop_search(search_props, 'tags_input', search_props, 'tags_list', icon='VIEWZOOM')
        draw_selected_tags(layout, search_props, f'object.{HANA3D_NAME}_remove_tag_search')
        layout.prop(search_props, 'public_only')
        label_multiline(layout, text=search_props.report)

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
