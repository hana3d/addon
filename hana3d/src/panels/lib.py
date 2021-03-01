"""Code used on multiple panels."""
import bpy

from ..preferences.preferences import Preferences
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


def draw_login_progress(layout):
    """Draw login progress.

    Parameters:
        layout: Blender layout
    """
    layout.label(text='Login through browser')
    layout.label(text='in progress.')
    layout.operator(f'wm.{HANA3D_NAME}_login_cancel', text='Cancel', icon='CANCEL')


def draw_login_buttons(layout):
    """Draw login buttons.

    Parameters:
        layout: Blender layout
    """
    user_preferences = Preferences().get()

    if user_preferences.login_attempt:
        draw_login_progress(layout)
    elif user_preferences.api_key == '':
        layout.operator(f'wm.{HANA3D_NAME}_login', text='Login / Sign up', icon='URL')
    else:
        layout.operator(f'wm.{HANA3D_NAME}_logout', text='Logout', icon='URL')


def label_multiline(layout, text='', icon='NONE', width=-1):  # noqa: WPS210
    """Draw a ui label, but try to split it in multiple lines.

    Parameters:
        layout: Blender layout
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
        layout.label(text=line, icon=icon)
        icon = 'NONE'


def draw_selected_tags(layout, props, operator):
    """Draw selected tags buttons.

    Parameters:
        layout: Blender layout
        props: Search or upload props
        operator: Blender operator function to remove tag
    """
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
    """Draw selected libraries buttons.

    Parameters:
        layout: Blender layout
        props: Search or upload props
        operator: Blender operator function to remove library
    """
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
