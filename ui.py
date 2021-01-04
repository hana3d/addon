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
"""Loads UI."""
import os

import bpy
from bpy.app.handlers import persistent
from bpy_extras import view3d_utils

from . import bg_blender, download, paths, render, utils
from .config import HANA3D_NAME, HANA3D_UI
from .src.preferences.preferences import Preferences
from .src.ui import bgl_helper, colors
from .src.ui.main import UI
from .src.ui.operators import (
    AssetBarOperator,
    DefaultNamesOperator,
    RunAssetBarWithContext,
    TransferHana3DData,
    UndoWithContext,
)


def draw_downloader(x, y, percent=0, img=None):  # noqa: WPS111
    """Draw downloader on screen.

    Parameters:
        x: x-coordinate where the downloader should be displayed
        y: y-coordinate where the downloader should be displayed
        percent: Downloader percentage
        img: Image to be displayed
    """
    width = 50
    if img is not None:
        height = 50
        bgl_helper.draw_image(x, y, width, height, img, 0.5)
    height = int(0.5 * percent)
    bgl_helper.draw_rect(x, y, width, height, (0.2, 1, 0.2, 0.3))
    bgl_helper.draw_rect(x - 3, y - 3, 6, 6, (1, 0, 0, 0.3))  # noqa: WPS221


def draw_progress(x, y, text='', percent=0, color=colors.GREEN):  # noqa: WPS111
    """Draw progress bar on screen.

    Parameters:
        x: x-coordinate where the progress bar should be drawn
        y: y-coordinate where the progress bar should be drawn
        text: Text to be displayed with the progress bar
        percent: Progress percentage
        color: color in which the progress bar should be drawn
    """
    font_size = 16
    bgl_helper.draw_rect(x, y, percent, 5, color)
    bgl_helper.draw_text(text, x, y + 8, font_size, color)


def draw_callback_progress3d(self, context):  # noqa: D103
    for thread in download.download_threads.values():
        if thread.asset_data['asset_type'] == 'model':
            for import_param in thread.tcom.passargs.get('import_params', []):
                bgl_helper.draw_bbox(
                    import_param['location'],
                    import_param['rotation'],
                    thread.asset_data['bbox_min'],
                    thread.asset_data['bbox_max'],
                    progress=thread.tcom.progress,
                )


def draw_callback_progress2d(self, context):  # noqa: D103
    ui = getattr(bpy.context.window_manager, HANA3D_UI)

    x = ui.reports_x  # noqa: WPS111
    y = ui.reports_y  # noqa: WPS111
    line_size = 30
    index = 0
    for download_thread in download.download_threads.values():
        asset_data = download_thread.asset_data
        tcom = download_thread.tcom

        directory = paths.get_temp_dir(f'{asset_data["asset_type"]}_search')
        tpath = os.path.join(directory, asset_data['thumbnail_small'])
        img = utils.get_hidden_image(tpath, asset_data['id'])

        if tcom.passargs.get('import_params'):
            for import_param in tcom.passargs['import_params']:
                loc = view3d_utils.location_3d_to_region_2d(
                    bpy.context.region,
                    bpy.context.space_data.region_3d,
                    import_param['location'],
                )
                if loc is not None:
                    # models now draw with star trek mode,
                    # no need to draw percent for the image.
                    draw_downloader(loc[0], loc[1], percent=tcom.progress, img=img)
        else:
            draw_progress(
                x,
                y - index * line_size,  # noqa: WPS204
                text=f'downloading {asset_data["name"]}',
                percent=tcom.progress,
            )
            index += 1
    for process in bg_blender.bg_processes:
        tcom = process[1]
        draw_progress(x, y - index * line_size, f'{tcom.lasttext}', tcom.progress)  # noqa: WPS221
        index += 1
    for render_thread in render.render_threads:
        percentage_progress = 0
        if render_thread.uploading:
            percentage_progress = int(render_thread.upload_progress * 100)
        elif render_thread.job_running:
            percentage_progress = int(render_thread.job_progress * 100)
        text = render_thread.render_state
        draw_progress(x, y - index * line_size, text, percentage_progress)
        index += 1
    for upload_thread in render.upload_threads:
        if upload_thread.uploading_render:
            text = upload_thread.upload_state
            percentage_progress = int(upload_thread.upload_progress * 100)
            draw_progress(x, y - index * line_size, text, percentage_progress)
            index += 1
    ui = UI()
    for report in ui.reports:
        report.draw(x, y - index * line_size)
        index += 1
        if report.fade():
            ui.reports.remove(report)


@persistent
def default_name_handler(dummy):  # noqa: D103
    context_dict = bpy.context.copy()
    context_dict.update(region='WINDOW')
    if bpy.context.area is None or bpy.context.area.type != 'VIEW_3D':
        window, area, region = UI().get_largest_view3d()
        override = {'window': window, 'screen': window.screen, 'area': area, 'region': region}
        context_dict.update(override)
    default_name_op = getattr(bpy.ops.view3d, f'{HANA3D_NAME}_default_name')
    default_name_op(context_dict, 'INVOKE_REGION_WIN')


# @persistent
def pre_load(context):  # noqa: D103
    ui_props = getattr(context.window_manager, HANA3D_UI)
    ui_props.assetbar_on = False
    ui_props.turn_off = True
    preferences = Preferences().get()
    preferences.login_attempt = False


def redraw_regions():  # noqa: D103
    for area in bpy.context.window.screen.areas:
        if area.type == 'VIEW_3D':
            for region in area.regions:
                if region.type == 'WINDOW':
                    region.tag_redraw()
    return 0.1


classes = (
    AssetBarOperator,
    DefaultNamesOperator,
    RunAssetBarWithContext,
    TransferHana3DData,
    UndoWithContext,
)

handler2d = None
handler3d = None
addon_keymapitems = []


def register():
    """Register ui in Blender."""
    global handler2d, handler3d, addon_keymapitems  # noqa: WPS420

    for c in classes:  # noqa: WPS111
        bpy.utils.register_class(c)

    args = (None, bpy.context)

    handler2d = bpy.types.SpaceView3D.draw_handler_add(  # noqa: WPS442
        draw_callback_progress2d,
        args,
        'WINDOW',
        'POST_PIXEL',
    )
    handler3d = bpy.types.SpaceView3D.draw_handler_add(  # noqa: WPS442
        draw_callback_progress3d,
        args,
        'WINDOW',
        'POST_VIEW',
    )

    wm = bpy.context.window_manager

    # spaces solved by registering shortcut to Window. Couldn't register object mode before somehow.
    if not wm.keyconfigs.addon:
        return
    km = wm.keyconfigs.addon.keymaps.new(name='Window', space_type='EMPTY')
    kmi = km.keymap_items.new(
        AssetBarOperator.bl_idname,
        'SEMI_COLON',
        'PRESS',
        ctrl=False,
        shift=False,
    )
    kmi.properties.keep_running = False
    kmi.properties.do_search = False
    addon_keymapitems.append(kmi)
    # auto open after searching:
    kmi = km.keymap_items.new(
        RunAssetBarWithContext.bl_idname,
        'SEMI_COLON',
        'PRESS',
        ctrl=True,
        shift=True,
        alt=True,
    )
    addon_keymapitems.append(kmi)

    bpy.app.handlers.load_post.append(default_name_handler)
    bpy.app.timers.register(redraw_regions)


def unregister():
    """Unregister ui in Blender."""
    global handler2d, handler3d, addon_keymapitems  # noqa: WPS420
    pre_load(bpy.context)

    bpy.app.handlers.load_post.remove(default_name_handler)

    bpy.types.SpaceView3D.draw_handler_remove(handler2d, 'WINDOW')
    bpy.types.SpaceView3D.draw_handler_remove(handler3d, 'WINDOW')

    for c in classes:  # noqa: WPS111
        bpy.utils.unregister_class(c)

    wm = bpy.context.window_manager
    if not wm.keyconfigs.addon:
        return

    km = wm.keyconfigs.addon.keymaps['Window']
    for kmi in addon_keymapitems:
        km.keymap_items.remove(kmi)
    addon_keymapitems = []  # noqa: WPS442
