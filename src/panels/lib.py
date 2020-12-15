"""Code used on multiple panels."""
import bpy

from ...config import HANA3D_NAME, HANA3D_UI


def draw_assetbar_show_hide(layout: bpy.types.UILayout) -> None:
    """Draw assetbat show/hide icon.

    Parameters:
        layout: UI Layout
    """
    wm = bpy.context.window_manager
    ui_props = getattr(wm, HANA3D_UI)

    if ui_props.assetbar_on:
        icon = 'HIDE_OFF'
        ttip = 'Click to Hide Asset Bar'
    else:
        icon = 'HIDE_ON'
        ttip = 'Click to Show Asset Bar'
    op = layout.operator(f'view3d.{HANA3D_NAME}_asset_bar', text='', icon=icon)
    op.keep_running = False
    op.do_search = False

    op.tooltip = ttip
