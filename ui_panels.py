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

from . import addon_updater_ops, utils
from .config import HANA3D_DESCRIPTION, HANA3D_MODELS, HANA3D_NAME, HANA3D_UI
from .src.panels.download import Hana3DDownloadPanel
from .src.panels.lib import draw_assetbar_show_hide
from .src.panels.login import Hana3DLoginPanel
from .src.panels.render import Hana3DRenderPanel
from .src.panels.unified import Hana3DUnifiedPanel
from .src.panels.updater import Hana3DUpdaterPanel
from .src.search.search import Search


def header_search_draw(self, context):
    '''Top bar menu in 3d view'''

    if not utils.guard_from_crash():
        return

    preferences = context.preferences.addons[HANA3D_NAME].preferences
    if preferences.search_in_header:
        layout = self.layout
        ui_props = getattr(context.window_manager, HANA3D_UI)
        search = Search(context)
        search_props = search.props

        if context.space_data.show_region_tool_header is True or context.mode[:4] not in (
            'EDIT',
            'OBJE',
        ):
            layout.separator_spacer()
        layout.prop(ui_props, 'asset_type', text='', icon='URL')
        layout.prop(search_props, 'search_keywords', text='', icon='VIEWZOOM')
        draw_assetbar_show_hide(layout)

classes = (
    Hana3DUpdaterPanel,
    Hana3DLoginPanel,
    Hana3DUnifiedPanel,
    Hana3DDownloadPanel,
    Hana3DRenderPanel,
)


def register():
    addon_updater_ops.make_annotations(Hana3DUpdaterPanel)
    for c in classes:
        bpy.utils.register_class(c)
    bpy.types.VIEW3D_MT_editor_menus.append(header_search_draw)


def unregister():
    for c in reversed(classes):
        bpy.utils.unregister_class(c)
    bpy.types.VIEW3D_MT_editor_menus.remove(header_search_draw)
