"""Panel builder."""
import bpy

from .download import Hana3DDownloadPanel
from .lib import draw_assetbar_show_hide, draw_login_buttons  # noqa: F401
from .login import Hana3DLoginPanel
from .logs import Hana3DSendLogsPanel
from .render import Hana3DRenderPanel
from .search import Hana3DSearchPanel
from .updater import Hana3DUpdaterPanel
from .upload import Hana3DUploadPanel
from ..search import search
from ... import utils
from ...config import HANA3D_NAME, HANA3D_UI


def header_search_draw(self, context):
    """Top bar menu in 3d view."""  # noqa: DAR101
    if not utils.guard_from_crash():
        return

    preferences = context.preferences.addons[HANA3D_NAME].preferences
    if preferences.search_in_header:
        layout = self.layout
        ui_props = getattr(context.window_manager, HANA3D_UI)
        search_props = search.get_search_props()

        if context.space_data.show_region_tool_header or context.mode[:4] not in {'EDIT', 'OBJE'}:
            layout.separator_spacer()
        layout.prop(ui_props, 'asset_type_search', text='', icon='URL')
        layout.prop(search_props, 'search_keywords', text='', icon='VIEWZOOM')
        draw_assetbar_show_hide(layout)


panels = (
    Hana3DUpdaterPanel,
    Hana3DLoginPanel,
    Hana3DSearchPanel,
    Hana3DUploadPanel,
    Hana3DDownloadPanel,
    Hana3DRenderPanel,
    Hana3DSendLogsPanel,
)


def register():
    """Register panel in Blender."""
    for panel in panels:
        bpy.utils.register_class(panel)
    bpy.types.VIEW3D_MT_editor_menus.append(header_search_draw)


def unregister():
    """Unregister panel in Blender."""
    for panel in reversed(panels):
        bpy.utils.unregister_class(panel)
    bpy.types.VIEW3D_MT_editor_menus.remove(header_search_draw)
