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
import logging
import math
import os
import time
from typing import List

import bpy
import mathutils
from bpy.app.handlers import persistent
from bpy.props import BoolProperty, StringProperty
from bpy_extras import view3d_utils
from mathutils import Vector

from . import bg_blender, colors, download, paths, render, search, utils
from .config import HANA3D_DESCRIPTION, HANA3D_MODELS, HANA3D_NAME, HANA3D_UI
from .report_tools import execute_wrapper
from .src.preferences.preferences import Preferences
from .src.search.search import Search
from .src.ui import bgl_helper
from .src.ui.report import Report

handler_2d = None
handler_3d = None
active_area = None
active_window = None
active_region = None

reports: List[Report] = []

mappingdict = {
    'MODEL': 'model',
    'SCENE': 'scene',
    'MATERIAL': 'material',
}

verification_icons = {
    'ready': 'vs_ready.png',
    'deleted': 'vs_deleted.png',
    'uploaded': 'vs_uploaded.png',
    'uploading': 'vs_uploading.png',
    'on_hold': 'vs_on_hold.png',
    'validated': None,
    'rejected': 'vs_rejected.png',
}


def add_report(text='', timeout=5, color=colors.GREEN):
    global reports
    global active_area  # noqa: WPS420
    # check for same reports and just make them longer by the timeout.
    for old_report in reports:
        if old_report.check_refresh(text, timeout):
            return
    logging.info(f'Message showed to the user: {text}')
    report = Report(active_area, text, timeout=timeout, color=color)
    reports.append(report)


def get_asset_under_mouse(mousex, mousey):
    ui_props = getattr(bpy.context.window_manager, HANA3D_UI)

    search_object = Search(bpy.context)
    search_results = search_object.results
    if search_results is not None:

        h_draw = min(ui_props.hcount, math.ceil(len(search_results) / ui_props.wcount))
        for b in range(0, h_draw):
            w_draw = min(
                ui_props.wcount,
                len(search_results) - b * ui_props.wcount - ui_props.scrolloffset
            )
            for a in range(0, w_draw):
                x = (
                    ui_props.bar_x
                    + a * (ui_props.margin + ui_props.thumb_size)
                    + ui_props.margin
                    + ui_props.drawoffset
                )
                y = (
                    ui_props.bar_y
                    - ui_props.margin
                    - (ui_props.thumb_size + ui_props.margin) * (b + 1)
                )
                w = ui_props.thumb_size
                h = ui_props.thumb_size

                if x < mousex < x + w and y < mousey < y + h:
                    return a + ui_props.wcount * b + ui_props.scrolloffset

                #   return search_results[a]

    return -3




def draw_tooltip(x, y, text='', author='', img=None, gravatar=None):
    region = bpy.context.region
    scale = bpy.context.preferences.view.ui_scale

    ttipmargin = 5
    textmargin = 10

    font_height = int(12 * scale)
    line_height = int(15 * scale)
    nameline_height = int(23 * scale)

    lines = text.split('\n')
    alines = author.split('\n')
    ncolumns = 2
    # nlines = math.ceil((len(lines) - 1) / ncolumns)
    nlines = max(len(lines) - 1, len(alines))  # math.ceil((len(lines) - 1) / ncolumns)

    texth = line_height * nlines + nameline_height

    if max(img.size[0], img.size[1]) == 0:
        return
    isizex = int(512 * scale * img.size[0] / max(img.size[0], img.size[1]))
    isizey = int(512 * scale * img.size[1] / max(img.size[0], img.size[1]))

    estimated_height = 2 * ttipmargin + textmargin + isizey

    if estimated_height > y:
        scaledown = y / (estimated_height)
        scale *= scaledown
        # we need to scale these down to have correct size if the tooltip wouldn't fit.
        font_height = int(12 * scale)
        line_height = int(15 * scale)
        nameline_height = int(23 * scale)

        lines = text.split('\n')

        texth = line_height * nlines + nameline_height
        isizex = int(512 * scale * img.size[0] / max(img.size[0], img.size[1]))
        isizey = int(512 * scale * img.size[1] / max(img.size[0], img.size[1]))

    name_height = int(18 * scale)

    x += 2 * ttipmargin
    y -= 2 * ttipmargin

    width = isizex + 2 * ttipmargin

    properties_width = 0
    for r in bpy.context.area.regions:
        if r.type == 'UI':
            properties_width = r.width

    x = min(x + width, region.width - properties_width) - width

    bgcol = bpy.context.preferences.themes[0].user_interface.wcol_tooltip.inner
    bgcol1 = (bgcol[0], bgcol[1], bgcol[2], 0.6)
    textcol = bpy.context.preferences.themes[0].user_interface.wcol_tooltip.text
    textcol = (textcol[0], textcol[1], textcol[2], 1)
    textcol_strong = (textcol[0] * 1.3, textcol[1] * 1.3, textcol[2] * 1.3, 1)

    # background
    bgl_helper.draw_rect(
        x - ttipmargin,
        y - 2 * ttipmargin - isizey,
        isizex + ttipmargin * 2,
        2 * ttipmargin + isizey,
        bgcol,
    )
    # main preview image
    bgl_helper.draw_image(x, y - isizey - ttipmargin, isizex, isizey, img, 1)

    # text overlay background
    bgl_helper.draw_rect(
        x - ttipmargin,
        y - 2 * ttipmargin - isizey,
        isizex + ttipmargin * 2,
        2 * ttipmargin + texth,
        bgcol1,
    )
    # draw gravatar
    gsize = 40
    if gravatar is not None:
        bgl_helper.draw_image(
            x + isizex / 2 + textmargin,
            y - isizey + texth - gsize - nameline_height - textmargin,
            gsize,
            gsize,
            gravatar,
            1,
        )

    i = 0
    column_lines = -1  # start minus one for the name
    xtext = x + textmargin
    fsize = name_height
    tcol = textcol

    for line in lines:
        ytext = (
            y
            - column_lines * line_height
            - nameline_height
            - ttipmargin
            - textmargin
            - isizey
            + texth
        )
        if i == 0:
            ytext = y - name_height + 5 - isizey + texth - textmargin
        elif i == len(lines) - 1:
            ytext = (
                y - (nlines - 1) * line_height - nameline_height - ttipmargin * 2 - isizey + texth
            )
            tcol = textcol
        else:
            if line[:4] == 'Tip:':
                tcol = textcol_strong
            fsize = font_height
        i += 1
        column_lines += 1
        bgl_helper.draw_text(line, xtext, ytext, fsize, tcol)
    xtext += int(isizex / ncolumns)

    column_lines = 1
    for line in alines:
        if gravatar is not None:
            if column_lines == 1:
                xtext += gsize + textmargin
            if column_lines == 4:
                xtext -= gsize + textmargin

        ytext = (
            y
            - column_lines * line_height
            - nameline_height
            - ttipmargin
            - textmargin
            - isizey
            + texth
        )
        if i == 0:
            ytext = y - name_height + 5 - isizey + texth - textmargin
        elif i == len(lines) - 1:
            ytext = (
                y - (nlines - 1) * line_height - nameline_height - ttipmargin * 2 - isizey + texth
            )
            tcol = textcol
        else:
            if line[:4] == 'Tip:':
                tcol = textcol_strong
            fsize = font_height
        i += 1
        column_lines += 1
        bgl_helper.draw_text(line, xtext, ytext, fsize, tcol)


def draw_callback_2d(self, context):
    if not utils.guard_from_crash():
        return

    a = context.area
    w = context.window
    try:
        # self.area might throw error just by itself.
        a1 = self.area
        w1 = self.window
        go = True
        if len(a.spaces[0].region_quadviews) > 0:
            if a.spaces[0].region_3d != context.region_data:
                go = False
    except Exception:
        # bpy.types.SpaceView3D.draw_handler_remove(self._handle_2d, 'WINDOW')
        # bpy.types.SpaceView3D.draw_handler_remove(self._handle_3d, 'WINDOW')
        go = False
    if go and a == a1 and w == w1:

        props = getattr(context.window_manager, HANA3D_UI)
        if props.down_up == 'SEARCH':
            draw_callback_2d_search(self, context)
        elif props.down_up == 'UPLOAD':
            draw_callback_2d_upload_preview(self, context)


def draw_downloader(x, y, percent=0, img=None):
    width = 50
    if img is not None:
        height = 50
        bgl_helper.draw_image(x, y, width, height, img, 0.5)
    height = int(0.5 * percent)
    bgl_helper.draw_rect(x, y, width, height, (0.2, 1, 0.2, 0.3))
    bgl_helper.draw_rect(x - 3, y - 3, 6, 6, (1, 0, 0, 0.3))  # noqa: WPS221


def draw_progress(x, y, text='', percent=None, color=colors.GREEN):  # noqa: WPS111
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


def draw_callback_3d_progress(self, context):
    # 'star trek' mode gets here, blocked by now ;)
    for thread in download.download_threads.values():
        if thread.asset_data['asset_type'] == 'model':
            for param in thread.tcom.passargs.get('import_params', []):
                bgl_helper.draw_bbox(
                    param['location'],
                    param['rotation'],
                    thread.asset_data['bbox_min'],
                    thread.asset_data['bbox_max'],
                    progress=thread.tcom.progress,
                )


def draw_callback_2d_progress(self, context):
    ui = getattr(bpy.context.window_manager, HANA3D_UI)

    x = ui.reports_x  # noqa: WPS111
    y = ui.reports_y  # noqa: WPS111
    line_size = 30
    index = 0
    for thread in download.download_threads.values():
        asset_data = thread.asset_data
        tcom = thread.tcom

        directory = paths.get_temp_dir('%s_search' % asset_data['asset_type'])
        tpath = os.path.join(directory, asset_data['thumbnail_small'])
        img = utils.get_hidden_image(tpath, asset_data['id'])

        if tcom.passargs.get('import_params'):
            for param in tcom.passargs['import_params']:
                loc = view3d_utils.location_3d_to_region_2d(
                    bpy.context.region,
                    bpy.context.space_data.region_3d,
                    param['location']
                )
                if loc is not None:
                    if asset_data['asset_type'] == 'model':
                        # models now draw with star trek mode,
                        # no need to draw percent for the image.
                        draw_downloader(loc[0], loc[1], percent=tcom.progress, img=img)
                    else:
                        draw_downloader(loc[0], loc[1], percent=tcom.progress, img=img)

        else:
            draw_progress(
                x,
                y - index * line_size,  # noqa: WPS204
                text=f'downloading {asset_data.name}',
                percent=tcom.progress,
            )
            index += 1
    for process in bg_blender.bg_processes:
        tcom = process[1]
        draw_progress(x, y - index * line_size, f'{tcom.lasttext}', tcom.progress)  # noqa: WPS221
        index += 1
    for thread in render.render_threads:
        percentage_progress = 0
        if thread.uploading:
            percentage_progress = int(thread.upload_progress * 100)
        elif thread.job_running:
            percentage_progress = int(thread.job_progress * 100)
        text = thread.render_state
        draw_progress(x, y - index * line_size, text, percentage_progress)
        index += 1
    for thread in render.upload_threads:  # noqa: WPS440
        if thread.uploading_render:
            text = thread.upload_state
            percentage_progress = int(thread.upload_progress * 100)
            draw_progress(x, y - index * line_size, text, percentage_progress)
            index += 1
    global reports  # noqa: WPS420
    for report in reports:
        report.draw(x, y - index * line_size)
        index += 1
        if report.fade():
            reports.remove(report)


def draw_callback_2d_upload_preview(self, context):
    ui_props = getattr(context.window_manager, HANA3D_UI)
    props = utils.get_upload_props()

    if props is not None and ui_props.draw_tooltip:
        ui_props.thumbnail_image = props.thumbnail

        if props.force_preview_reload:
            force_reload = True
            props.force_preview_reload = False
        else:
            force_reload = False

        if props.remote_thumbnail:
            default_image = 'thumbnail-in-progress.png'
        else:
            default_image = 'thumbnail_notready.png'

        img = utils.get_hidden_image(
            ui_props.thumbnail_image,
            'upload_preview',
            force_reload,
            default_image,
        )
        draw_tooltip(ui_props.bar_x, ui_props.bar_y, text=ui_props.tooltip, img=img)


def draw_callback_2d_search(self, context):
    wm = context.window_manager
    ui_props = getattr(wm, HANA3D_UI)

    search_result = self.region
    # hc = bpy.context.preferences.themes[0].view_3d.space.header
    # hc = bpy.context.preferences.themes[0].user_interface.wcol_menu_back.inner
    # hc = (hc[0], hc[1], hc[2], .2)
    hc = (1, 1, 1, 0.07)
    white = (1, 1, 1, 0.2)
    green = (0.2, 1, 0.2, 0.7)
    highlight = bpy.context.preferences.themes[0].user_interface.wcol_menu_item.inner_sel
    highlight = (1, 1, 1, 0.2)
    # highlight = (1, 1, 1, 0.8)
    # background of asset bar
    if not ui_props.dragging:
        search_object = Search(bpy.context)
        search_results = search_object.results
        search_results_orig = search_object.results_orig
        if search_results is None:
            return
        h_draw = min(ui_props.hcount, math.ceil(len(search_results) / ui_props.wcount))

        if ui_props.wcount > len(search_results):
            bar_width = (
                len(search_results) * (ui_props.thumb_size + ui_props.margin) + ui_props.margin
            )
        else:
            bar_width = ui_props.bar_width
        row_height = ui_props.thumb_size + ui_props.margin
        bgl_helper.draw_rect(
            ui_props.bar_x,
            ui_props.bar_y - ui_props.bar_height,
            bar_width,
            ui_props.bar_height,
            hc,
        )

        if search_results is not None:
            count = ui_props.wcount * ui_props.hcount
            if ui_props.scrolloffset > 0 or count < len(search_results):
                ui_props.drawoffset = 35
            else:
                ui_props.drawoffset = 0

            if count < len(search_results):
                page_start = ui_props.scrolloffset + 1
                preferences = Preferences().get()
                page_end = ui_props.scrolloffset + ui_props.wcount * preferences.max_assetbar_rows
                pagination_text = \
                    f'{page_start} - {page_end} of {search_object.results_orig["count"]}'  # noqa E501
                bgl_helper.draw_text(
                    pagination_text,
                    ui_props.bar_x + ui_props.bar_width - 125,  # noqa: WPS432
                    ui_props.bar_y - ui_props.bar_height - 25,  # noqa: WPS432
                    14,  # noqa: WPS432
                )
                # arrows
                arrow_y = (
                    ui_props.bar_y
                    - int((ui_props.bar_height + ui_props.thumb_size) / 2)
                    + ui_props.margin
                )
                width = 25
                if ui_props.scrolloffset > 0:

                    if ui_props.active_index == -2:
                        bgl_helper.draw_rect(  # noqa: WPS220
                            ui_props.bar_x,
                            ui_props.bar_y - ui_props.bar_height,
                            width,
                            ui_props.bar_height,
                            highlight,
                        )
                    img = utils.get_thumbnail('arrow_left.png')
                    bgl_helper.draw_image(
                        ui_props.bar_x,
                        arrow_y,
                        width,
                        ui_props.thumb_size,
                        img,
                        1,
                    )

                if search_results_orig['count'] - ui_props.scrolloffset > count + 1:
                    if ui_props.active_index == -1:
                        bgl_helper.draw_rect(  # noqa: WPS220
                            ui_props.bar_x + ui_props.bar_width - width,
                            ui_props.bar_y - ui_props.bar_height,
                            width,
                            ui_props.bar_height,
                            highlight,
                        )
                    img1 = utils.get_thumbnail('arrow_right.png')
                    bgl_helper.draw_image(
                        ui_props.bar_x + ui_props.bar_width - width,
                        arrow_y,
                        width,
                        ui_props.thumb_size,
                        img1,
                        1,
                    )

            for b in range(0, h_draw):
                w_draw = min(
                    ui_props.wcount,
                    len(search_results) - b * ui_props.wcount - ui_props.scrolloffset,
                )

                y = ui_props.bar_y - (b + 1) * (row_height)
                for a in range(0, w_draw):
                    x = (
                        ui_props.bar_x
                        + a * (ui_props.margin + ui_props.thumb_size)
                        + ui_props.margin
                        + ui_props.drawoffset
                    )

                    index = a + ui_props.scrolloffset + b * ui_props.wcount
                    iname = utils.previmg_name(index)
                    img = bpy.data.images.get(iname)

                    max_size = max(img.size[0], img.size[1])
                    width = int(ui_props.thumb_size * img.size[0] / max_size)
                    height = int(ui_props.thumb_size * img.size[1] / max_size)
                    crop = (0, 0, 1, 1)
                    if img.size[0] > img.size[1]:
                        offset = (1 - img.size[1] / img.size[0]) / 2  # noqa: WPS220, WPS221
                        crop = (offset, 0, 1 - offset, 1)  # noqa: WPS220
                    if img is not None:
                        bgl_helper.draw_image(x, y, width, width, img, 1, crop=crop)  # noqa: WPS220
                        if index == ui_props.active_index:  # noqa: WPS220
                            bgl_helper.draw_rect(  # noqa: WPS220
                                x - ui_props.highlight_margin,
                                y - ui_props.highlight_margin,
                                width + 2 * ui_props.highlight_margin,
                                width + 2 * ui_props.highlight_margin,
                                highlight,
                            )
                        # if index == ui_props.active_index:
                        #     ui_bgl.draw_rect(x - highlight_margin, y - highlight_margin,
                        #               w + 2*highlight_margin, h + 2*highlight_margin , highlight)

                    else:
                        bgl_helper.draw_rect(x, y, width, height, white)  # noqa: WPS220

                    result = search_results[index]
                    if result['downloaded'] > 0:
                        width = int(width * result['downloaded'] / 100.0)  # noqa: WPS220
                        bgl_helper.draw_rect(x, y - 2, width, 2, green)  # noqa: WPS220
                    # object type icons - just a test..., adds clutter/ not so userfull:
                    # icons = ('type_finished.png', 'type_template.png', 'type_particle_system.png')

                    v_icon = verification_icons[result.get('verification_status', 'validated')]
                    if v_icon is not None:
                        img = utils.get_thumbnail(v_icon)
                        bgl_helper.draw_image(  # noqa: WPS220
                            x + ui_props.thumb_size - 26,  # noqa: WPS432
                            y + 2,
                            24,
                            24,
                            img,
                            1,
                        )


        props = getattr(wm, HANA3D_UI)
        if props.draw_tooltip:
            # TODO move this lazy loading into a function and don't duplicate through the code
            iname = utils.previmg_name(ui_props.active_index, fullsize=True)

            directory = paths.get_temp_dir('%s_search' % mappingdict[props.asset_type])
            search_results = search_object.results
            if search_results is not None and -1 < ui_props.active_index < len(search_results):
                search_result = search_results[ui_props.active_index]
                tpath = os.path.join(directory, search_result['thumbnail'])

                img = bpy.data.images.get(iname)
                if img is None or img.filepath != tpath:
                    # TODO replace it with a function
                    if os.path.exists(tpath):

                        if img is None:
                            img = bpy.data.images.load(tpath)
                            img.name = iname
                        else:
                            if img.filepath != tpath:
                                # todo replace imgs reloads with a method
                                # that forces unpack for thumbs.
                                if img.packed_file is not None:
                                    img.unpack(method='USE_ORIGINAL')
                                img.filepath = tpath
                                img.reload()
                                img.name = iname
                    else:
                        iname = utils.previmg_name(ui_props.active_index)
                        img = bpy.data.images.get(iname)
                    img.colorspace_settings.name = 'Linear'

                gimg = None
                atip = ''
                if bpy.context.window_manager.get(f'{HANA3D_NAME}_authors') is not None:
                    a = bpy.context.window_manager[f'{HANA3D_NAME}_authors'].get(  # noqa : WPS111,WPS440
                        search_result['author_id'],
                    )
                    if a is not None and a != '':
                        if a.get('gravatarImg') is not None:
                            gimg = utils.get_hidden_image(a['gravatarImg'], a['gravatarHash'])
                        atip = a['tooltip']

                draw_tooltip(
                    ui_props.mouse_x,
                    ui_props.mouse_y,
                    text=ui_props.tooltip,
                    author=atip,
                    img=img,
                    gravatar=gimg,
                )

    if ui_props.dragging and (ui_props.draw_drag_image or ui_props.draw_snapped_bounds):
        if ui_props.active_index > -1:
            iname = utils.previmg_name(ui_props.active_index)
            img = bpy.data.images.get(iname)
            linelength = 35
            bgl_helper.draw_image(
                ui_props.mouse_x + linelength,
                ui_props.mouse_y - linelength - ui_props.thumb_size,
                ui_props.thumb_size,
                ui_props.thumb_size,
                img,
                1,
            )
            bgl_helper.draw_line2d(
                ui_props.mouse_x,
                ui_props.mouse_y,
                ui_props.mouse_x + linelength,
                ui_props.mouse_y - linelength,
                2,
                white,
            )


def draw_callback_3d(self, context):
    ''' Draw snapped bbox while dragging and in the future other Hana3D related stuff. '''
    if not utils.guard_from_crash():
        return

    ui = getattr(context.window_manager, HANA3D_UI)

    if ui.dragging and ui.asset_type == 'MODEL':
        if ui.draw_snapped_bounds:
            bgl_helper.draw_bbox(
                ui.snapped_location,
                ui.snapped_rotation,
                ui.snapped_bbox_min,
                ui.snapped_bbox_max
            )


def mouse_raycast(context, mx, my):
    r = context.region
    rv3d = context.region_data
    coord = mx, my

    # get the ray from the viewport and mouse
    view_vector = view3d_utils.region_2d_to_vector_3d(r, rv3d, coord)
    ray_origin = view3d_utils.region_2d_to_origin_3d(r, rv3d, coord)
    ray_target = ray_origin + (view_vector * 1000000000)

    vec = ray_target - ray_origin

    (
        has_hit,
        snapped_location,
        snapped_normal,
        face_index,
        object,
        matrix,
    ) = bpy.context.scene.ray_cast(bpy.context.view_layer, ray_origin, vec)

    # rote = mathutils.Euler((0, 0, math.pi))
    randoffset = math.pi
    if has_hit:
        snapped_rotation = snapped_normal.to_track_quat('Z', 'Y').to_euler()
        up = Vector((0, 0, 1))
        props = getattr(bpy.context.window_manager, HANA3D_MODELS)
        if snapped_normal.angle(up) < math.radians(10.0):
            randoffset = props.offset_rotation_amount + math.pi
        else:
            # we don't rotate this way on walls and ceilings. + math.pi
            randoffset = props.offset_rotation_amount
        # snapped_rotation.z += math.pi + (random.random() - 0.5) * .2

    else:
        snapped_rotation = mathutils.Quaternion((0, 0, 0, 0)).to_euler()

    snapped_rotation.rotate_axis('Z', randoffset)

    return has_hit, snapped_location, snapped_normal, snapped_rotation, face_index, object, matrix


def floor_raycast(context, mx, my):
    r = context.region
    rv3d = context.region_data
    coord = mx, my

    # get the ray from the viewport and mouse
    view_vector = view3d_utils.region_2d_to_vector_3d(r, rv3d, coord)
    ray_origin = view3d_utils.region_2d_to_origin_3d(r, rv3d, coord)
    ray_target = ray_origin + (view_vector * 1000)

    # various intersection plane normals are needed for corner cases
    # that might actually happen quite often - in front and side view.
    # default plane normal is scene floor.
    plane_normal = (0, 0, 1)
    if (
        math.isclose(view_vector.x, 0, abs_tol=1e-4)
        and math.isclose(view_vector.z, 0, abs_tol=1e-4)
    ):
        plane_normal = (0, 1, 0)
    elif math.isclose(view_vector.z, 0, abs_tol=1e-4):
        plane_normal = (1, 0, 0)

    snapped_location = mathutils.geometry.intersect_line_plane(
        ray_origin,
        ray_target,
        (0, 0, 0),
        plane_normal,
        False
    )
    if snapped_location is not None:
        has_hit = True
        snapped_normal = Vector((0, 0, 1))
        face_index = None
        object = None
        matrix = None
        snapped_rotation = snapped_normal.to_track_quat('Z', 'Y').to_euler()
        props = getattr(bpy.context.window_manager, HANA3D_MODELS)
        randoffset = props.offset_rotation_amount + math.pi
        snapped_rotation.rotate_axis('Z', randoffset)

    return has_hit, snapped_location, snapped_normal, snapped_rotation, face_index, object, matrix


def mouse_in_area(mx, my, x, y, w, h):
    if x < mx < x + w and y < my < y + h:
        return True
    else:
        return False


def mouse_in_asset_bar(mx, my):
    ui_props = getattr(bpy.context.window_manager, HANA3D_UI)

    if (
        ui_props.bar_y - ui_props.bar_height < my < ui_props.bar_y
        and mx > ui_props.bar_x
        and mx < ui_props.bar_x + ui_props.bar_width
    ):
        return True
    else:
        return False


def mouse_in_region(r, mx, my):
    if 0 < my < r.height and 0 < mx < r.width:
        return True
    else:
        return False


def update_ui_size(area, region):
    wm = bpy.context.window_manager
    ui = getattr(wm, HANA3D_UI)
    user_preferences = bpy.context.preferences.addons[HANA3D_NAME].preferences
    ui_scale = bpy.context.preferences.view.ui_scale

    ui.margin = ui.bl_rna.properties['margin'].default * ui_scale
    ui.thumb_size = user_preferences.thumb_size * ui_scale

    reg_multiplier = 1
    if not bpy.context.preferences.system.use_region_overlap:
        reg_multiplier = 0

    for r in area.regions:
        if r.type == 'TOOLS':
            ui.bar_x = r.width * reg_multiplier + ui.margin + ui.bar_x_offset * ui_scale
        elif r.type == 'UI':
            ui.bar_end = r.width * reg_multiplier + 100 * ui_scale

    ui.bar_width = region.width - ui.bar_x - ui.bar_end
    ui.wcount = math.floor((ui.bar_width - 2 * ui.drawoffset) / (ui.thumb_size + ui.margin))

    search_object = Search(bpy.context)
    search_results = search_object.results
    if search_results is not None and ui.wcount > 0:
        ui.hcount = min(
            user_preferences.max_assetbar_rows,
            math.ceil(len(search_results) / ui.wcount)
        )
    else:
        ui.hcount = 1
    ui.bar_height = (ui.thumb_size + ui.margin) * ui.hcount + ui.margin
    ui.bar_y = region.height - ui.bar_y_offset * ui_scale
    if ui.down_up == 'UPLOAD':
        ui.reports_y = ui.bar_y - 600
        ui.reports_x = ui.bar_x
    else:
        ui.reports_y = ui.bar_y - ui.bar_height - 100
        ui.reports_x = ui.bar_x


def get_largest_3dview():
    maxsurf = 0
    maxa = None
    maxw = None
    region = None
    for w in bpy.context.window_manager.windows:
        screen = w.screen
        for a in screen.areas:
            if a.type == 'VIEW_3D':
                asurf = a.width * a.height
                if asurf > maxsurf:
                    maxa = a
                    maxw = w
                    maxsurf = asurf

                    for r in a.regions:
                        if r.type == 'WINDOW':
                            region = r
    global active_area, active_window, active_region
    active_window = maxw
    active_area = maxa
    active_region = region
    return maxw, maxa, region


class AssetBarOperator(bpy.types.Operator):
    '''runs search and displays the asset bar at the same time'''

    bl_idname = f"view3d.{HANA3D_NAME}_asset_bar"
    bl_label = f"{HANA3D_DESCRIPTION} Asset Bar UI"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    do_search: BoolProperty(name="Run Search", description='', default=True, options={'SKIP_SAVE'})
    keep_running: BoolProperty(
        name="Keep Running",
        description='',
        default=True,
        options={'SKIP_SAVE'}
    )

    tooltip: bpy.props.StringProperty(
        default='runs search and displays the asset bar at the same time'
    )

    @classmethod
    def description(cls, context, properties):
        return properties.tooltip

    def search_more(self):
        """Search more results."""
        search_object = Search(bpy.context)
        search_results_orig = search_object.results_orig
        if search_results_orig is not None and search_results_orig.get('next') is not None:
            search.search(get_next=True)

    def exit_modal(self):
        try:
            bpy.types.SpaceView3D.draw_handler_remove(self._handle_2d, 'WINDOW')
            bpy.types.SpaceView3D.draw_handler_remove(self._handle_3d, 'WINDOW')
        except Exception:
            pass
        ui_props = getattr(bpy.context.window_manager, HANA3D_UI)

        ui_props.dragging = False
        ui_props.tooltip = ''
        ui_props.active_index = -3
        ui_props.draw_drag_image = False
        ui_props.draw_snapped_bounds = False
        ui_props.has_hit = False
        ui_props.assetbar_on = False

    def modal(self, context, event):
        # This is for case of closing the area or changing type:
        ui_props = getattr(context.window_manager, HANA3D_UI)
        areas = []

        if bpy.context.scene != self.scene:
            self.exit_modal()
            return {'CANCELLED'}

        for w in context.window_manager.windows:
            areas.extend(w.screen.areas)

        if (
            self.area not in areas
            or self.area.type != 'VIEW_3D'
            or self.has_quad_views != (len(self.area.spaces[0].region_quadviews) > 0)
        ):
            # logging.info('search areas')   bpy.context.area.spaces[0].region_quadviews
            # stopping here model by now - because of:
            #   switching layouts or maximizing area now fails to assign new area throwing the bug
            #   internal error: modal gizmo-map handler has invalid area
            self.exit_modal()
            return {'CANCELLED'}

            newarea = None
            for a in context.window.screen.areas:
                if a.type == 'VIEW_3D':
                    self.area = a
                    for r in a.regions:
                        if r.type == 'WINDOW':
                            self.region = r
                    newarea = a
                    break
                    # context.area = a

            # we check again and quit if things weren't fixed this way.
            if newarea is None:
                self.exit_modal()
                return {'CANCELLED'}

        update_ui_size(self.area, self.region)

        # this was here to check if sculpt stroke is running, but obviously that didn't help,
        # since the RELEASE event is cought by operator and thus
        # there is no way to detect a stroke has ended...
        if bpy.context.mode in ('SCULPT', 'PAINT_TEXTURE'):
            # ASSUME THAT SCULPT OPERATOR ACTUALLY STEALS THESE EVENTS,
            if event.type == 'MOUSEMOVE':
                bpy.context.window_manager['appendable'] = True
            if event.type == 'LEFTMOUSE':
                if event.value == 'PRESS':
                    bpy.context.window_manager['appendable'] = False

        self.area.tag_redraw()
        scene = context.scene

        if ui_props.turn_off:
            ui_props.turn_off = False
            self.exit_modal()
            ui_props.draw_tooltip = False
            return {'CANCELLED'}

        if context.region != self.region:
            return {'PASS_THROUGH'}

        if ui_props.down_up == 'UPLOAD':

            ui_props.mouse_x = 0
            ui_props.mouse_y = self.region.height

            mx = event.mouse_x
            my = event.mouse_y

            ui_props.draw_tooltip = True

            # only generate tooltip once in a while
            if (
                (event.type == 'LEFTMOUSE' or event.type == 'RIGHTMOUSE')
                and event.value == 'RELEASE'
                or event.type == 'ENTER'
                or ui_props.tooltip == ''
            ):
                ao = bpy.context.active_object
                if (
                    ui_props.asset_type == 'MODEL'
                    and ao is not None
                    or ui_props.asset_type == 'MATERIAL'
                    and ao is not None
                    and ao.active_material is not None
                ):
                    props = utils.get_upload_props()
                    asset_data = {
                        'name': props.name,
                        'description': props.description,
                        'dimensions': getattr(props, 'dimensions', None),
                        'face_count': getattr(props, 'face_count', None),
                        'face_count_render': getattr(props, 'face_count_render', None),
                        'object_count': getattr(props, 'object_count', None),
                    }
                    ui_props.tooltip = utils.generate_tooltip(**asset_data)

            return {'PASS_THROUGH'}

        # TODO add one more condition here to take less performance.
        r = self.region
        scene = bpy.context.scene
        search_object = Search(context)
        search_results = search_object.results
        search_results_orig = search_object.results_orig
        # If there aren't any results, we need no interaction(yet)
        if search_results is None:
            return {'PASS_THROUGH'}
        if len(search_results) - ui_props.scrolloffset < (ui_props.wcount * ui_props.hcount) + 10:  # noqa : WPS221,WPS204
            self.search_more()
        if (
            event.type == 'WHEELUPMOUSE'
            or event.type == 'WHEELDOWNMOUSE'
            or event.type == 'TRACKPADPAN'
        ):
            # scrolling
            mx = event.mouse_region_x
            my = event.mouse_region_y

            if ui_props.dragging and not mouse_in_asset_bar(mx, my):
                # and my < r.height - ui_props.bar_height \
                # and mx > 0 and mx < r.width and my > 0:
                sprops = getattr(context.window_manager, HANA3D_MODELS)
                if event.type == 'WHEELUPMOUSE':
                    sprops.offset_rotation_amount += sprops.offset_rotation_step
                elif event.type == 'WHEELDOWNMOUSE':
                    sprops.offset_rotation_amount -= sprops.offset_rotation_step

                # TODO - this snapping code below is 3x in this file.... refactor it.
                (
                    ui_props.has_hit,
                    ui_props.snapped_location,
                    ui_props.snapped_normal,
                    ui_props.snapped_rotation,
                    face_index,
                    object,
                    matrix,
                ) = mouse_raycast(context, mx, my)

                # MODELS can be dragged on scene floor
                if not ui_props.has_hit and ui_props.asset_type == 'MODEL':
                    (
                        ui_props.has_hit,
                        ui_props.snapped_location,
                        ui_props.snapped_normal,
                        ui_props.snapped_rotation,
                        face_index,
                        object,
                        matrix,
                    ) = floor_raycast(context, mx, my)

                return {'RUNNING_MODAL'}

            if not mouse_in_asset_bar(mx, my):
                return {'PASS_THROUGH'}

            if (
                (event.type == 'WHEELDOWNMOUSE')
                and len(search_results) - ui_props.scrolloffset > (ui_props.wcount * ui_props.hcount)  # noqa : E501
            ):
                if ui_props.hcount > 1:
                    ui_props.scrolloffset += ui_props.wcount
                else:
                    ui_props.scrolloffset += 1
                if len(search_results) - ui_props.scrolloffset < (ui_props.wcount * ui_props.hcount):  # noqa : N400
                    ui_props.scrolloffset = len(search_results) - (ui_props.wcount * ui_props.hcount)  # noqa : E501

            if event.type == 'WHEELUPMOUSE' and ui_props.scrolloffset > 0:
                if ui_props.hcount > 1:
                    ui_props.scrolloffset -= ui_props.wcount
                else:
                    ui_props.scrolloffset -= 1
                if ui_props.scrolloffset < 0:
                    ui_props.scrolloffset = 0

            return {'RUNNING_MODAL'}
        if event.type == 'MOUSEMOVE':  # Apply

            r = self.region
            mx = event.mouse_region_x
            my = event.mouse_region_y

            ui_props.mouse_x = mx
            ui_props.mouse_y = my

            if ui_props.drag_init:
                ui_props.drag_length += 1
                if ui_props.drag_length > 0:
                    ui_props.dragging = True
                    ui_props.drag_init = False

            if (
                not (ui_props.dragging and mouse_in_region(r, mx, my))
                and not mouse_in_asset_bar(mx, my)
            ):
                ui_props.dragging = False
                ui_props.has_hit = False
                ui_props.active_index = -3
                ui_props.draw_drag_image = False
                ui_props.draw_snapped_bounds = False
                ui_props.draw_tooltip = False
                bpy.context.window.cursor_set("DEFAULT")
                return {'PASS_THROUGH'}

            search_object = Search(bpy.context)
            search_results = search_object.results

            if not ui_props.dragging:
                bpy.context.window.cursor_set("DEFAULT")

                if (  # noqa : WPS337
                    search_results is not None
                    and ui_props.wcount * ui_props.hcount > len(search_results)
                    and ui_props.scrolloffset > 0
                ):
                    ui_props.scrolloffset = 0

                asset_search_index = get_asset_under_mouse(mx, my)
                ui_props.active_index = asset_search_index
                if asset_search_index > -1:

                    asset_data = search_results[asset_search_index]
                    ui_props.draw_tooltip = True

                    ui_props.tooltip = asset_data['tooltip']

                else:
                    ui_props.draw_tooltip = False

                if (
                    mx > ui_props.bar_x + ui_props.bar_width - 50
                    and search_results_orig['count'] - ui_props.scrolloffset
                    > (ui_props.wcount * ui_props.hcount) + 1
                ):
                    ui_props.active_index = -1
                    return {'RUNNING_MODAL'}
                if mx < ui_props.bar_x + 50 and ui_props.scrolloffset > 0:
                    ui_props.active_index = -2
                    return {'RUNNING_MODAL'}

            else:
                if ui_props.dragging and mouse_in_region(r, mx, my):
                    (
                        ui_props.has_hit,
                        ui_props.snapped_location,
                        ui_props.snapped_normal,
                        ui_props.snapped_rotation,
                        face_index,
                        object,
                        matrix,
                    ) = mouse_raycast(context, mx, my)
                    # MODELS can be dragged on scene floor
                    if not ui_props.has_hit and ui_props.asset_type == 'MODEL':
                        (
                            ui_props.has_hit,
                            ui_props.snapped_location,
                            ui_props.snapped_normal,
                            ui_props.snapped_rotation,
                            face_index,
                            object,
                            matrix,
                        ) = floor_raycast(context, mx, my)
                if ui_props.has_hit and ui_props.asset_type == 'MODEL':
                    # this condition is here to fix a bug for a scene
                    # submitted by a user, so this situation shouldn't
                    # happen anymore, but there might exists scenes
                    # which have this problem for some reason.
                    if ui_props.active_index < len(search_results) and ui_props.active_index > -1:  # noqa : WPS333
                        ui_props.draw_snapped_bounds = True  # noqa : WPS220
                        active_mod = search_results[ui_props.active_index]  # noqa : WPS220
                        ui_props.snapped_bbox_min = Vector(active_mod['bbox_min'])  # noqa : WPS220
                        ui_props.snapped_bbox_max = Vector(active_mod['bbox_max'])  # noqa : WPS220

                else:
                    ui_props.draw_snapped_bounds = False
                    ui_props.draw_drag_image = True
            return {'RUNNING_MODAL'}

        if event.type == 'RIGHTMOUSE':
            mx = event.mouse_x - r.x
            my = event.mouse_y - r.y

        if event.type == 'LEFTMOUSE':

            r = self.region
            mx = event.mouse_x - r.x
            my = event.mouse_y - r.y

            ui_props = getattr(context.window_manager, HANA3D_UI)
            if event.value == 'PRESS' and ui_props.active_index > -1:
                if ui_props.asset_type == 'MODEL' or ui_props.asset_type == 'MATERIAL':
                    # check if asset is locked and let the user know in that case
                    asset_search_index = ui_props.active_index
                    asset_data = search_results[asset_search_index]
                    # go on with drag init
                    ui_props.drag_init = True
                    bpy.context.window.cursor_set("NONE")
                    ui_props.draw_tooltip = False
                    ui_props.drag_length = 0
                elif ui_props.asset_type == 'SCENE':
                    ui_props.drag_init = True
                    bpy.context.window.cursor_set("NONE")
                    ui_props.draw_tooltip = False
                    ui_props.drag_length = 0

            if not ui_props.dragging and not mouse_in_asset_bar(mx, my):
                return {'PASS_THROUGH'}

            # this can happen by switching result asset types - length of search result changes
            if (
                ui_props.scrolloffset > 0
                and (ui_props.wcount * ui_props.hcount) > len(search_results) - ui_props.scrolloffset  # noqa : E501
            ):
                ui_props.scrolloffset = len(search_results) - (ui_props.wcount * ui_props.hcount)  # noqa : E501

            if event.value == 'RELEASE':  # Confirm
                ui_props.drag_init = False

                # scroll by a whole page
                if (
                    mx > ui_props.bar_x + ui_props.bar_width - 50  # noqa : WPS432
                    and len(search_results) - ui_props.scrolloffset > ui_props.wcount * ui_props.hcount  # noqa : E501
                ):
                    ui_props.scrolloffset = min(
                        ui_props.scrolloffset + (ui_props.wcount * ui_props.hcount),
                        len(search_results) - ui_props.wcount * ui_props.hcount,
                    )
                    return {'RUNNING_MODAL'}
                if mx < ui_props.bar_x + 50 and ui_props.scrolloffset > 0:
                    ui_props.scrolloffset = max(
                        0,
                        ui_props.scrolloffset - ui_props.wcount * ui_props.hcount
                    )
                    return {'RUNNING_MODAL'}

                # Drag-drop interaction
                if ui_props.dragging and mouse_in_region(r, mx, my):
                    asset_search_index = ui_props.active_index
                    # raycast here
                    ui_props.active_index = -3

                    if ui_props.asset_type == 'MODEL':

                        (
                            ui_props.has_hit,
                            ui_props.snapped_location,
                            ui_props.snapped_normal,
                            ui_props.snapped_rotation,
                            face_index,
                            object,
                            matrix,
                        ) = mouse_raycast(context, mx, my)

                        # MODELS can be dragged on scene floor
                        if not ui_props.has_hit and ui_props.asset_type == 'MODEL':
                            (
                                ui_props.has_hit,
                                ui_props.snapped_location,
                                ui_props.snapped_normal,
                                ui_props.snapped_rotation,
                                face_index,
                                object,
                                matrix,
                            ) = floor_raycast(context, mx, my)

                        if not ui_props.has_hit:
                            return {'RUNNING_MODAL'}

                        target_object = ''
                        if object is not None:
                            target_object = object.name
                        target_slot = ''

                    if ui_props.asset_type == 'MATERIAL':
                        (
                            ui_props.has_hit,
                            ui_props.snapped_location,
                            ui_props.snapped_normal,
                            ui_props.snapped_rotation,
                            face_index,
                            object,
                            matrix,
                        ) = mouse_raycast(context, mx, my)

                        if not ui_props.has_hit:
                            # this is last attempt to get object under mouse
                            # for curves and other objects than mesh.
                            ui_props.dragging = False
                            sel = utils.selection_get()
                            bpy.ops.view3d.select(
                                location=(event.mouse_region_x, event.mouse_region_y)
                            )
                            sel1 = utils.selection_get()
                            if sel[0] != sel1[0] and sel1[0].type != 'MESH':
                                object = sel1[0]
                                target_slot = sel1[0].active_material_index
                                ui_props.has_hit = True
                            utils.selection_set(sel)

                        if not ui_props.has_hit:
                            return {'RUNNING_MODAL'}

                        else:
                            # first, test if object can have material applied.
                            # TODO add other types here if droppable.
                            if (
                                object is not None
                                and not object.is_library_indirect
                                and object.type == 'MESH'
                            ):
                                target_object = object.name
                                # create final mesh to extract correct material slot
                                depsgraph = bpy.context.evaluated_depsgraph_get()
                                object_eval = object.evaluated_get(depsgraph)
                                temp_mesh = object_eval.to_mesh()
                                target_slot = temp_mesh.polygons[face_index].material_index
                                object_eval.to_mesh_clear()
                            else:
                                logging.warning('Invalid or library object as input:') # noqa WPS220
                                target_object = ''
                                target_slot = ''

                # Click interaction
                else:
                    asset_search_index = get_asset_under_mouse(mx, my)

                    if ui_props.asset_type in ('MATERIAL', 'MODEL',):  # noqa : WPS220
                        ao = bpy.context.active_object
                        if ao is not None and not ao.is_library_indirect:
                            target_object = bpy.context.active_object.name
                            target_slot = bpy.context.active_object.active_material_index
                        else:
                            target_object = ''
                            target_slot = ''
                # FIRST START SEARCH

                if asset_search_index == -3:
                    return {'RUNNING_MODAL'}
                if asset_search_index > -3:
                    if ui_props.asset_type == 'MATERIAL':
                        if target_object != '':
                            # position is for downloader:
                            loc = ui_props.snapped_location
                            rotation = (0, 0, 0)

                            asset_data = search_results[asset_search_index]  # noqa : WPS220
                            download_op = getattr(bpy.ops.scene, f'{HANA3D_NAME}_download')  # noqa : WPS220
                            download_op(
                                True,
                                asset_type=ui_props.asset_type,
                                asset_index=asset_search_index,
                                model_location=loc,
                                model_rotation=rotation,
                                target_object=target_object,
                                material_target_slot=target_slot,
                            )

                    elif ui_props.asset_type == 'MODEL':
                        if ui_props.has_hit and ui_props.dragging:
                            loc = ui_props.snapped_location
                            rotation = ui_props.snapped_rotation
                        else:
                            loc = scene.cursor.location  # noqa : WPS220
                            rotation = scene.cursor.rotation_euler  # noqa : WPS220

                        download_op = getattr(bpy.ops.scene, HANA3D_NAME + "_download")
                        download_op(
                            True,
                            asset_type=ui_props.asset_type,
                            asset_index=asset_search_index,
                            model_location=loc,
                            model_rotation=rotation,
                            target_object=target_object,
                        )

                    else:
                        download_op = getattr(bpy.ops.scene, HANA3D_NAME + "_download")
                        download_op(
                            asset_type=ui_props.asset_type,
                            asset_index=asset_search_index
                        )

                    ui_props.dragging = False
                    return {'RUNNING_MODAL'}
            else:
                return {'RUNNING_MODAL'}
        return {'PASS_THROUGH'}

    def invoke(self, context, event):
        # FIRST START SEARCH
        ui_props = getattr(context.window_manager, HANA3D_UI)

        if self.do_search:
            search.search()

        if ui_props.assetbar_on:
            # we don't want to run the assetbar many times,
            # that's why it has a switch on/off behaviour,
            # unless being called with 'keep_running' prop.
            if not self.keep_running:
                # this sends message to the originally running operator,
                # so it quits, and then it ends this one too.
                # If it initiated a search, the search will finish in a thread.
                # The switch off procedure is run
                # by the 'original' operator, since if we get here, it means
                # same operator is already running.
                ui_props.turn_off = True
                # if there was an error, we need to turn off
                # these props so we can restart after 2 clicks
                ui_props.assetbar_on = False

            else:
                pass
            return {'FINISHED'}

        ui_props.dragging = False  # only for cases where assetbar ended with an error.
        ui_props.assetbar_on = True
        ui_props.turn_off = False

        search_object = Search(bpy.context)
        search_results = search_object.results
        if search_results is None:
            search_object = Search(bpy.context)
            search_object.results = []  # noqa : WPS110

        if context.area.type != 'VIEW_3D':
            logging.warning('View3D not found, cannot run operator')
            return {'CANCELLED'}

        # the arguments we pass the the callback
        args = (self, context)

        self.window = context.window
        self.area = context.area
        self.scene = bpy.context.scene

        self.has_quad_views = len(bpy.context.area.spaces[0].region_quadviews) > 0

        for r in self.area.regions:
            if r.type == 'WINDOW':
                self.region = r

        global active_window, active_area, active_region
        active_window = self.window
        active_area = self.area
        active_region = self.region

        update_ui_size(self.area, self.region)

        self._handle_2d = bpy.types.SpaceView3D.draw_handler_add(
            draw_callback_2d,
            args,
            'WINDOW',
            'POST_PIXEL'
        )
        self._handle_3d = bpy.types.SpaceView3D.draw_handler_add(
            draw_callback_3d,
            args,
            'WINDOW',
            'POST_VIEW'
        )

        context.window_manager.modal_handler_add(self)
        ui_props.assetbar_on = True
        return {'RUNNING_MODAL'}

    @execute_wrapper
    def execute(self, context):
        return {'RUNNING_MODAL'}


class DefaultNamesOperator(bpy.types.Operator):
    '''Assign default object name as props name and object render job name'''

    bl_idname = f"view3d.{HANA3D_NAME}_default_name"
    bl_label = f"{HANA3D_DESCRIPTION} Default Name"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    def modal(self, context, event):
        # This is for case of closing the area or changing type:
        ui_props = getattr(context.window_manager, HANA3D_UI)

        if ui_props.turn_off:
            return {'CANCELLED'}

        draw_event = (
            event.type == 'LEFTMOUSE' or event.type == 'RIGHTMOUSE' or event.type == 'ENTER'
        )
        if not draw_event:
            return {'PASS_THROUGH'}

        if ui_props.down_up == 'SEARCH':
            search_object = Search(context)
            search_props = search_object.props
            if (
                search_props.workspace != ''
                and len(search_props.tags_list) == 0
            ):
                search_props.workspace = search_props.workspace

        asset = utils.get_active_asset()
        if asset is None:
            return {'PASS_THROUGH'}

        props = getattr(asset, HANA3D_NAME)

        if ui_props.down_up == 'UPLOAD':
            if props.workspace != '' and len(props.tags_list) == 0:
                props.workspace = props.workspace
            if props.name == '' and props.name != asset.name:
                props.name = asset.name

        if props.render_job_name == '':
            if 'jobs' not in props.render_data:
                previous_names = []
            else:
                previous_names = [job['job_name'] for job in props.render_data['jobs']]
            name = props.name or asset.name or 'Render'
            for n in range(1000):
                new_name = f'{name}_{n:03d}'
                if new_name not in previous_names:
                    break
            props.render_job_name = new_name

        return {'PASS_THROUGH'}

    def invoke(self, context, event):
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}


class TransferHana3DData(bpy.types.Operator):
    """Regenerate cobweb"""

    bl_idname = f"object.{HANA3D_NAME}_data_transfer"
    bl_label = f"Transfer {HANA3D_DESCRIPTION} data"
    bl_description = "Transfer hana3d metadata from one object to another when fixing uploads with wrong parenting."  # noqa E501
    bl_options = {'REGISTER', 'UNDO'}

    @execute_wrapper
    def execute(self, context):
        source_ob = bpy.context.active_object
        for target_ob in bpy.context.selected_objects:
            if target_ob != source_ob:
                target_ob.property_unset(HANA3D_NAME)
                for k in source_ob.keys():
                    target_ob[k] = source_ob[k]
        source_ob.property_unset(HANA3D_NAME)
        return {'FINISHED'}


class UndoWithContext(bpy.types.Operator):
    """Regenerate cobweb"""

    bl_idname = f"wm.{HANA3D_NAME}_undo_push_context"
    bl_label = f"{HANA3D_DESCRIPTION} undo push"
    bl_description = f"{HANA3D_DESCRIPTION} undo push with fixed context"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    # def modal(self, context, event):
    #     return {'RUNNING_MODAL'}

    message: StringProperty('Undo Message', default=f'{HANA3D_DESCRIPTION} operation')

    @execute_wrapper
    def execute(self, context):
        C_dict = bpy.context.copy()
        C_dict.update(region='WINDOW')
        if context.area is None or context.area.type != 'VIEW_3D':
            w, a, r = get_largest_3dview()
            override = {'window': w, 'screen': w.screen, 'area': a, 'region': r}
            C_dict.update(override)
        bpy.ops.ed.undo_push(C_dict, 'INVOKE_REGION_WIN', message=self.message)
        return {'FINISHED'}


class RunAssetBarWithContext(bpy.types.Operator):
    """Regenerate cobweb"""

    bl_idname = f"object.{HANA3D_NAME}_run_assetbar_fix_context"
    bl_label = f"{HANA3D_DESCRIPTION} assetbar with fixed context"
    bl_description = "Run assetbar with fixed context"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    # def modal(self, context, event):
    #     return {'RUNNING_MODAL'}

    @execute_wrapper
    def execute(self, context):
        C_dict = bpy.context.copy()
        C_dict.update(region='WINDOW')
        if context.area is None or context.area.type != 'VIEW_3D':
            w, a, r = get_largest_3dview()
            override = {'window': w, 'screen': w.screen, 'area': a, 'region': r}
            C_dict.update(override)
        asset_bar_op = getattr(bpy.ops.view3d, f'{HANA3D_NAME}_asset_bar')
        asset_bar_op(
            C_dict,
            'INVOKE_REGION_WIN',
            keep_running=True,
            do_search=False
        )
        return {'FINISHED'}


classes = (
    AssetBarOperator,
    DefaultNamesOperator,
    RunAssetBarWithContext,
    TransferHana3DData,
    UndoWithContext,
)

# store keymap items here to access after registration
addon_keymapitems = []


@persistent
def default_name_handler(dummy):
    C_dict = bpy.context.copy()
    C_dict.update(region='WINDOW')
    if bpy.context.area is None or bpy.context.area.type != 'VIEW_3D':
        w, a, r = get_largest_3dview()
        override = {'window': w, 'screen': w.screen, 'area': a, 'region': r}
        C_dict.update(override)
    default_name_op = getattr(bpy.ops.view3d, f'{HANA3D_NAME}_default_name')
    default_name_op(C_dict, 'INVOKE_REGION_WIN')


# @persistent
def pre_load(context):
    ui_props = getattr(bpy.context.window_manager, HANA3D_UI)
    ui_props.assetbar_on = False
    ui_props.turn_off = True
    preferences = bpy.context.preferences.addons[HANA3D_NAME].preferences
    preferences.login_attempt = False


def redraw_regions():
    for area in bpy.context.window.screen.areas:
        if area.type == 'VIEW_3D':
            for region in area.regions:
                if region.type == 'WINDOW':
                    region.tag_redraw()
    return 0.1


def register():
    global handler_2d, handler_3d

    for c in classes:
        bpy.utils.register_class(c)

    args = (None, bpy.context)

    handler_2d = bpy.types.SpaceView3D.draw_handler_add(
        draw_callback_2d_progress,
        args,
        'WINDOW',
        'POST_PIXEL'
    )
    handler_3d = bpy.types.SpaceView3D.draw_handler_add(
        draw_callback_3d_progress,
        args,
        'WINDOW',
        'POST_VIEW'
    )

    wm = bpy.context.window_manager

    # spaces solved by registering shortcut to Window. Couldn't register object mode before somehow.
    if not wm.keyconfigs.addon:
        return
    km = wm.keyconfigs.addon.keymaps.new(name="Window", space_type='EMPTY')
    kmi = km.keymap_items.new(
        AssetBarOperator.bl_idname,
        'SEMI_COLON',
        'PRESS',
        ctrl=False,
        shift=False
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
        alt=True
    )
    addon_keymapitems.append(kmi)

    bpy.app.handlers.load_post.append(default_name_handler)
    bpy.app.timers.register(redraw_regions)


def unregister():
    global handler_2d, handler_3d
    pre_load(bpy.context)

    bpy.app.handlers.load_post.remove(default_name_handler)

    bpy.types.SpaceView3D.draw_handler_remove(handler_2d, 'WINDOW')
    bpy.types.SpaceView3D.draw_handler_remove(handler_3d, 'WINDOW')

    for c in classes:
        bpy.utils.unregister_class(c)

    wm = bpy.context.window_manager
    if not wm.keyconfigs.addon:
        return

    km = wm.keyconfigs.addon.keymaps['Window']
    for kmi in addon_keymapitems:
        km.keymap_items.remove(kmi)
    del addon_keymapitems[:]
