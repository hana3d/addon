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

if 'bpy' in locals():
    from importlib import reload

    bg_blender = reload(bg_blender)
    colors = reload(colors)
    download = reload(download)
    paths = reload(paths)
    render = reload(render)
    search = reload(search)
    ui_bgl = reload(ui_bgl)
    utils = reload(utils)
else:
    from hana3d import (
        bg_blender,
        colors,
        download,
        paths,
        render,
        search,
        ui_bgl,
        utils
    )

import math
import os
import time

import bpy
import mathutils
from bpy.app.handlers import persistent
from bpy.props import BoolProperty, StringProperty
from bpy_extras import view3d_utils
from mathutils import Vector

handler_2d = None
handler_3d = None
active_area = None
active_area = None
active_window = None
active_region = None

reports = []

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


def get_approximate_text_width(st):
    size = 10
    for s in st:
        if s in 'i|':
            size += 2
        elif s in ' ':
            size += 4
        elif s in 'sfrt':
            size += 5
        elif s in 'ceghkou':
            size += 6
        elif s in 'PadnBCST3E':
            size += 7
        elif s in 'GMODVXYZ':
            size += 8
        elif s in 'w':
            size += 9
        elif s in 'm':
            size += 10
        else:
            size += 7
    return size  # Convert to picas


def add_report(text='', timeout=5, color=colors.GREEN):
    global reports
    # check for same reports and just make them longer by the timeout.
    for old_report in reports:
        if old_report.text == text:
            old_report.timeout = old_report.age + timeout
            return
    report = Report(text=text, timeout=timeout, color=color)
    reports.append(report)


class Report:
    def __init__(self, text='', timeout=5, color=(0.5, 1, 0.5, 1)):
        self.text = text
        self.timeout = timeout
        self.start_time = time.time()
        self.color = color
        self.draw_color = color
        self.age = 0

    def fade(self):
        fade_time = 1
        self.age = time.time() - self.start_time
        if self.age + fade_time > self.timeout:
            alpha_multiplier = (self.timeout - self.age) / fade_time
            self.draw_color = (
                self.color[0],
                self.color[1],
                self.color[2],
                self.color[3] * alpha_multiplier,
            )
            if self.age > self.timeout:
                global reports
                try:
                    reports.remove(self)
                except Exception:
                    pass

    def draw(self, x, y):
        if bpy.context.area == active_area:
            ui_bgl.draw_text(self.text, x, y + 8, 16, self.draw_color)


def get_asset_under_mouse(mousex, mousey):
    wm = bpy.context.window_manager
    ui_props = bpy.context.window_manager.Hana3DUI

    search_results = wm.get('search results')
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


def draw_bbox(location, rotation, bbox_min, bbox_max, progress=None, color=(0, 1, 0, 1)):
    rotation = mathutils.Euler(rotation)

    smin = Vector(bbox_min)
    smax = Vector(bbox_max)
    v0 = Vector(smin)
    v1 = Vector((smax.x, smin.y, smin.z))
    v2 = Vector((smax.x, smax.y, smin.z))
    v3 = Vector((smin.x, smax.y, smin.z))
    v4 = Vector((smin.x, smin.y, smax.z))
    v5 = Vector((smax.x, smin.y, smax.z))
    v6 = Vector((smax.x, smax.y, smax.z))
    v7 = Vector((smin.x, smax.y, smax.z))

    arrowx = smin.x + (smax.x - smin.x) / 2
    arrowy = smin.y - (smax.x - smin.x) / 2
    v8 = Vector((arrowx, arrowy, smin.z))

    vertices = [v0, v1, v2, v3, v4, v5, v6, v7, v8]
    for v in vertices:
        v.rotate(rotation)
        v += Vector(location)

    lines = [
        [0, 1],
        [1, 2],
        [2, 3],
        [3, 0],
        [4, 5],
        [5, 6],
        [6, 7],
        [7, 4],
        [0, 4],
        [1, 5],
        [2, 6],
        [3, 7],
        [0, 8],
        [1, 8],
    ]
    ui_bgl.draw_lines(vertices, lines, color)
    if progress is not None:
        color = (color[0], color[1], color[2], 0.2)
        progress = progress * 0.01
        vz0 = (v4 - v0) * progress + v0
        vz1 = (v5 - v1) * progress + v1
        vz2 = (v6 - v2) * progress + v2
        vz3 = (v7 - v3) * progress + v3
        rects = ((v0, v1, vz1, vz0), (v1, v2, vz2, vz1), (v2, v3, vz3, vz2), (v3, v0, vz0, vz3))
        for r in rects:
            ui_bgl.draw_rect_3d(r, color)


def draw_text_block(x=0, y=0, width=40, font_size=10, line_height=15, text='', color=colors.TEXT):
    lines = text.split('\n')
    nlines = []
    for line in lines:
        nlines.extend(search.split_subs(line,))

    column_lines = 0
    for line in nlines:
        ytext = y - column_lines * line_height
        column_lines += 1
        ui_bgl.draw_text(line, x, ytext, font_size, color)


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
    ui_bgl.draw_rect(
        x - ttipmargin,
        y - 2 * ttipmargin - isizey,
        isizex + ttipmargin * 2,
        2 * ttipmargin + isizey,
        bgcol,
    )
    # main preview image
    ui_bgl.draw_image(x, y - isizey - ttipmargin, isizex, isizey, img, 1)

    # text overlay background
    ui_bgl.draw_rect(
        x - ttipmargin,
        y - 2 * ttipmargin - isizey,
        isizex + ttipmargin * 2,
        2 * ttipmargin + texth,
        bgcol1,
    )
    # draw gravatar
    gsize = 40
    if gravatar is not None:
        ui_bgl.draw_image(
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
        ui_bgl.draw_text(line, xtext, ytext, fsize, tcol)
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
        ui_bgl.draw_text(line, xtext, ytext, fsize, tcol)


def draw_tooltip_old(x, y, text='', author='', img=None):
    region = bpy.context.region
    scale = bpy.context.preferences.view.ui_scale

    ttipmargin = 10

    font_height = int(12 * scale)
    line_height = int(15 * scale)
    nameline_height = int(23 * scale)

    lines = text.split('\n')
    ncolumns = 2
    nlines = math.ceil((len(lines) - 1) / ncolumns)
    texth = line_height * nlines + nameline_height

    isizex = int(512 * scale * img.size[0] / max(img.size[0], img.size[1]))
    isizey = int(512 * scale * img.size[1] / max(img.size[0], img.size[1]))

    estimated_height = texth + 3 * ttipmargin + isizey

    if estimated_height > y:
        scaledown = y / (estimated_height)
        scale *= scaledown
        # we need to scale these down to have correct size if the tooltip wouldn't fit.
        font_height = int(12 * scale)
        line_height = int(15 * scale)
        nameline_height = int(23 * scale)

        lines = text.split('\n')
        ncolumns = 2
        nlines = math.ceil((len(lines) - 1) / ncolumns)
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
    textcol = bpy.context.preferences.themes[0].user_interface.wcol_tooltip.text
    textcol = (textcol[0], textcol[1], textcol[2], 1)
    textcol1 = (textcol[0] * 0.8, textcol[1] * 0.8, textcol[2] * 0.8, 1)

    ui_bgl.draw_rect(
        x - ttipmargin,
        y - texth - 2 * ttipmargin - isizey,
        isizex + ttipmargin * 2,
        texth + 3 * ttipmargin + isizey,
        bgcol,
    )

    i = 0
    column_lines = -1  # start minus one for the name
    xtext = x
    fsize = name_height
    tcol = textcol
    for line in lines:
        if column_lines >= nlines:
            xtext += int(isizex / ncolumns)
            column_lines = 0
        ytext = y - column_lines * line_height - nameline_height - ttipmargin
        if i == 0:
            ytext = y - name_height + 5
        elif i == len(lines) - 1:
            ytext = y - (nlines - 1) * line_height - nameline_height - ttipmargin
            tcol = textcol
        else:
            if line[:5] == 'tags:':
                tcol = textcol1
            fsize = font_height
        i += 1
        column_lines += 1
        ui_bgl.draw_text(line, xtext, ytext, fsize, tcol)
    ui_bgl.draw_image(x, y - texth - isizey - ttipmargin, isizex, isizey, img, 1)


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
            # print(dir(bpy.context.region_data))
            # print('quad', a.spaces[0].region_3d, a.spaces[0].region_quadviews[0])
            if a.spaces[0].region_3d != context.region_data:
                go = False
    except Exception:
        # bpy.types.SpaceView3D.draw_handler_remove(self._handle_2d, 'WINDOW')
        # bpy.types.SpaceView3D.draw_handler_remove(self._handle_3d, 'WINDOW')
        go = False
    if go and a == a1 and w == w1:

        props = context.window_manager.Hana3DUI
        if props.down_up == 'SEARCH':
            draw_callback_2d_search(self, context)
        elif props.down_up == 'UPLOAD':
            draw_callback_2d_upload_preview(self, context)


def draw_downloader(x, y, percent=0, img=None):
    if img is not None:
        ui_bgl.draw_image(x, y, 50, 50, img, 0.5)
    ui_bgl.draw_rect(x, y, 50, int(0.5 * percent), (0.2, 1, 0.2, 0.3))
    ui_bgl.draw_rect(x - 3, y - 3, 6, 6, (1, 0, 0, 0.3))


def draw_progress(x, y, text='', percent=None, color=colors.GREEN):
    ui_bgl.draw_rect(x, y, percent, 5, color)
    ui_bgl.draw_text(text, x, y + 8, 16, color)


def draw_callback_3d_progress(self, context):
    # 'star trek' mode gets here, blocked by now ;)
    for thread in download.download_threads.values():
        if thread.asset_data['asset_type'] == 'model':
            for param in thread.tcom.passargs.get('import_params', []):
                draw_bbox(
                    param['location'],
                    param['rotation'],
                    thread.asset_data['bbox_min'],
                    thread.asset_data['bbox_max'],
                    progress=thread.tcom.progress,
                )


def draw_callback_2d_progress(self, context):
    ui = bpy.context.window_manager.Hana3DUI

    x = ui.reports_x
    y = ui.reports_y
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
                y - index * 30,
                text='downloading %s' % asset_data['name'],
                percent=tcom.progress
            )
            index += 1
    for process in bg_blender.bg_processes:
        tcom = process[1]
        draw_progress(x, y - index * 30, '%s' % tcom.lasttext, tcom.progress)
        index += 1
    for thread in render.render_threads:
        if thread.uploading:
            text = thread.props.render_state
            draw_progress(x, y - index * 30, text, int(thread.upload_progress * 100))
            index += 1
        elif thread.job_running:
            text = thread.props.render_state
            draw_progress(x, y - index * 30, text, int(thread.job_progress * 100))
            index += 1
    for thread in render.upload_threads:
        if thread.props.uploading_render:
            text = thread.props.upload_state
            draw_progress(x, y - index * 30, text, int(thread.upload_progress * 100))
            index += 1
    global reports
    for report in reports:
        report.draw(x, y - index * 30)
        index += 1
        report.fade()


def draw_callback_2d_upload_preview(self, context):
    ui_props = context.window_manager.Hana3DUI

    props = utils.get_upload_props()
    if props is not None and ui_props.draw_tooltip:

        ui_props.thumbnail_image = props.thumbnail

        img = utils.get_hidden_image(ui_props.thumbnail_image, 'upload_preview')

        draw_tooltip(ui_props.bar_x, ui_props.bar_y, text=ui_props.tooltip, img=img)


def draw_callback_2d_search(self, context):
    wm = context.window_manager
    ui_props = wm.Hana3DUI

    r = self.region
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
        search_results = wm.get('search results')
        search_results_orig = wm.get('search results orig')
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
        ui_bgl.draw_rect(
            ui_props.bar_x,
            ui_props.bar_y - ui_props.bar_height,
            bar_width,
            ui_props.bar_height,
            hc
        )

        if search_results is not None:
            if ui_props.scrolloffset > 0 or ui_props.wcount * ui_props.hcount < len(search_results):
                ui_props.drawoffset = 35
            else:
                ui_props.drawoffset = 0

            if ui_props.wcount * ui_props.hcount < len(search_results):
                # arrows
                arrow_y = (
                    ui_props.bar_y
                    - int((ui_props.bar_height + ui_props.thumb_size) / 2)
                    + ui_props.margin
                )
                if ui_props.scrolloffset > 0:

                    if ui_props.active_index == -2:
                        ui_bgl.draw_rect(
                            ui_props.bar_x,
                            ui_props.bar_y - ui_props.bar_height,
                            25,
                            ui_props.bar_height,
                            highlight,
                        )
                    img = utils.get_thumbnail('arrow_left.png')
                    ui_bgl.draw_image(ui_props.bar_x, arrow_y, 25, ui_props.thumb_size, img, 1)

                if (
                    search_results_orig['count'] - ui_props.scrolloffset
                    > (ui_props.wcount * ui_props.hcount) + 1
                ):
                    if ui_props.active_index == -1:
                        ui_bgl.draw_rect(
                            ui_props.bar_x + ui_props.bar_width - 25,
                            ui_props.bar_y - ui_props.bar_height,
                            25,
                            ui_props.bar_height,
                            highlight,
                        )
                    img1 = utils.get_thumbnail('arrow_right.png')
                    ui_bgl.draw_image(
                        ui_props.bar_x + ui_props.bar_width - 25,
                        arrow_y,
                        25,
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

                    #
                    index = a + ui_props.scrolloffset + b * ui_props.wcount
                    iname = utils.previmg_name(index)
                    img = bpy.data.images.get(iname)

                    w = int(ui_props.thumb_size * img.size[0] / max(img.size[0], img.size[1]))
                    h = int(ui_props.thumb_size * img.size[1] / max(img.size[0], img.size[1]))
                    crop = (0, 0, 1, 1)
                    if img.size[0] > img.size[1]:
                        offset = (1 - img.size[1] / img.size[0]) / 2
                        crop = (offset, 0, 1 - offset, 1)
                    if img is not None:
                        ui_bgl.draw_image(x, y, w, w, img, 1, crop=crop)
                        if index == ui_props.active_index:
                            ui_bgl.draw_rect(
                                x - ui_props.highlight_margin,
                                y - ui_props.highlight_margin,
                                w + 2 * ui_props.highlight_margin,
                                w + 2 * ui_props.highlight_margin,
                                highlight,
                            )
                        # if index == ui_props.active_index:
                        #     ui_bgl.draw_rect(x - highlight_margin, y - highlight_margin,
                        #               w + 2*highlight_margin, h + 2*highlight_margin , highlight)

                    else:
                        ui_bgl.draw_rect(x, y, w, h, white)

                    result = search_results[index]
                    if result['downloaded'] > 0:
                        ui_bgl.draw_rect(x, y - 2, int(w * result['downloaded'] / 100.0), 2, green)
                    # object type icons - just a test..., adds clutter/ not so userfull:
                    # icons = ('type_finished.png', 'type_template.png', 'type_particle_system.png')

                    v_icon = verification_icons[result.get('verification_status', 'validated')]
                    if v_icon is not None:
                        img = utils.get_thumbnail(v_icon)
                        ui_bgl.draw_image(x + ui_props.thumb_size - 26, y + 2, 24, 24, img, 1)

            # if user_preferences.api_key == '':
            #     report = 'Register on hana3d website to upload your own assets.'
            #     ui_bgl.draw_text(report, ui_props.bar_x + ui_props.margin,
            #                      ui_props.bar_y - 25 - ui_props.margin - ui_props.bar_height, 15)
            # elif len(search_results) == 0:
            #     report = 'hana3d - No matching results found.'
            #     ui_bgl.draw_text(report, ui_props.bar_x + ui_props.margin,
            #                      ui_props.bar_y - 25 - ui_props.margin, 15)
        props = utils.get_search_props()
        # if props.report != '' and props.is_searching or props.search_error:
        #     ui_bgl.draw_text(props.report, ui_props.bar_x,
        #                      ui_props.bar_y - 15 - ui_props.margin - ui_props.bar_height, 15)

        props = wm.Hana3DUI
        if props.draw_tooltip:
            # TODO move this lazy loading into a function and don't duplicate through the code
            iname = utils.previmg_name(ui_props.active_index, fullsize=True)

            directory = paths.get_temp_dir('%s_search' % mappingdict[props.asset_type])
            sr = wm.get('search results')
            if sr is not None and -1 < ui_props.active_index < len(sr):
                r = sr[ui_props.active_index]
                tpath = os.path.join(directory, r['thumbnail'])

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
                if bpy.context.window_manager.get('hana3d authors') is not None:
                    a = bpy.context.window_manager['hana3d authors'].get(r['author_id'])
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

    if (
        ui_props.dragging
        and (ui_props.draw_drag_image or ui_props.draw_snapped_bounds)
        and ui_props.active_index > -1
    ):
        iname = utils.previmg_name(ui_props.active_index)
        img = bpy.data.images.get(iname)
        linelength = 35
        ui_bgl.draw_image(
            ui_props.mouse_x + linelength,
            ui_props.mouse_y - linelength - ui_props.thumb_size,
            ui_props.thumb_size,
            ui_props.thumb_size,
            img,
            1,
        )
        ui_bgl.draw_line2d(
            ui_props.mouse_x,
            ui_props.mouse_y,
            ui_props.mouse_x + linelength,
            ui_props.mouse_y - linelength,
            2,
            white,
        )


def draw_callback_3d(self, context):
    ''' Draw snapped bbox while dragging and in the future other hana3d related stuff. '''
    if not utils.guard_from_crash():
        return

    ui = context.window_manager.Hana3DUI

    if ui.dragging and ui.asset_type == 'MODEL':
        if ui.draw_snapped_bounds:
            draw_bbox(
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
        props = bpy.context.window_manager.hana3d_models
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
        props = bpy.context.window_manager.hana3d_models
        randoffset = props.offset_rotation_amount + math.pi
        snapped_rotation.rotate_axis('Z', randoffset)

    return has_hit, snapped_location, snapped_normal, snapped_rotation, face_index, object, matrix


def mouse_in_area(mx, my, x, y, w, h):
    if x < mx < x + w and y < my < y + h:
        return True
    else:
        return False


def mouse_in_asset_bar(mx, my):
    ui_props = bpy.context.window_manager.Hana3DUI

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
    ui = bpy.context.window_manager.Hana3DUI
    user_preferences = bpy.context.preferences.addons['hana3d'].preferences
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

    search_results = bpy.context.window_manager.get('search results')
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

    bl_idname = "view3d.hana3d_asset_bar"
    bl_label = "Hana3D Asset Bar UI"
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
        sro = bpy.context.window_manager.get('search results orig')
        if sro is not None and sro.get('next') is not None:
            search.search(get_next=True)

    def exit_modal(self):
        try:
            bpy.types.SpaceView3D.draw_handler_remove(self._handle_2d, 'WINDOW')
            bpy.types.SpaceView3D.draw_handler_remove(self._handle_3d, 'WINDOW')
        except Exception:
            pass
        ui_props = bpy.context.window_manager.Hana3DUI

        ui_props.dragging = False
        ui_props.tooltip = ''
        ui_props.active_index = -3
        ui_props.draw_drag_image = False
        ui_props.draw_snapped_bounds = False
        ui_props.has_hit = False
        ui_props.assetbar_on = False

    def modal(self, context, event):
        # This is for case of closing the area or changing type:
        ui_props = context.window_manager.Hana3DUI
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
            # print('search areas')   bpy.context.area.spaces[0].region_quadviews
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
        s = context.scene

        if ui_props.turn_off:
            ui_props.turn_off = False
            self.exit_modal()
            ui_props.draw_tooltip = False
            return {'CANCELLED'}

        if context.region != self.region:
            # print(time.time(), 'pass through because of region')
            # print(context.region.type, self.region.type)
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
                    upload_data = utils.get_export_data(ui_props.asset_type)[1]
                    ui_props.tooltip = search.generate_tooltip(upload_data)

            return {'PASS_THROUGH'}

        # TODO add one more condition here to take less performance.
        r = self.region
        s = bpy.context.scene
        wm = context.window_manager
        sr = wm.get('search results')
        search_results_orig = wm.get('search results orig')
        # If there aren't any results, we need no interaction(yet)
        if sr is None:
            return {'PASS_THROUGH'}
        if len(sr) - ui_props.scrolloffset < (ui_props.wcount * ui_props.hcount) + 10:
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
                sprops = wm.hana3d_models
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

            # note - TRACKPADPAN is unsupported in blender by now.
            # if event.type == 'TRACKPADPAN' :
            #     print(dir(event))
            #     print(event.value, event.oskey, event.)
            if (
                (event.type == 'WHEELDOWNMOUSE')
                and len(sr) - ui_props.scrolloffset > (ui_props.wcount * ui_props.hcount)
            ):
                if ui_props.hcount > 1:
                    ui_props.scrolloffset += ui_props.wcount
                else:
                    ui_props.scrolloffset += 1
                if len(sr) - ui_props.scrolloffset < (ui_props.wcount * ui_props.hcount):
                    ui_props.scrolloffset = len(sr) - (ui_props.wcount * ui_props.hcount)

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

            sr = bpy.context.window_manager['search results']

            if not ui_props.dragging:
                bpy.context.window.cursor_set("DEFAULT")

                if (
                    sr is not None
                    and ui_props.wcount * ui_props.hcount > len(sr)
                    and ui_props.scrolloffset > 0
                ):
                    ui_props.scrolloffset = 0

                asset_search_index = get_asset_under_mouse(mx, my)
                ui_props.active_index = asset_search_index
                if asset_search_index > -1:

                    asset_data = sr[asset_search_index]
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
                    if ui_props.active_index < len(sr) and ui_props.active_index > -1:
                        ui_props.draw_snapped_bounds = True
                        active_mod = sr[ui_props.active_index]
                        ui_props.snapped_bbox_min = Vector(active_mod['bbox_min'])
                        ui_props.snapped_bbox_max = Vector(active_mod['bbox_max'])

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

            ui_props = context.window_manager.Hana3DUI
            if event.value == 'PRESS' and ui_props.active_index > -1:
                if ui_props.asset_type == 'MODEL' or ui_props.asset_type == 'MATERIAL':
                    # check if asset is locked and let the user know in that case
                    asset_search_index = ui_props.active_index
                    asset_data = sr[asset_search_index]
                    # go on with drag init
                    ui_props.drag_init = True
                    bpy.context.window.cursor_set("NONE")
                    ui_props.draw_tooltip = False
                    ui_props.drag_length = 0
                elif ui_props.asset_type == 'SCENE':
                    context.window_manager.Hana3DUI.drag_init = True
                    bpy.context.window.cursor_set("NONE")
                    context.window_manager.Hana3DUI.draw_tooltip = False
                    context.window_manager.Hana3DUI.drag_length = 0

            if not ui_props.dragging and not mouse_in_asset_bar(mx, my):
                return {'PASS_THROUGH'}

            # this can happen by switching result asset types - length of search result changes
            if (
                ui_props.scrolloffset > 0
                and (ui_props.wcount * ui_props.hcount) > len(sr) - ui_props.scrolloffset
            ):
                ui_props.scrolloffset = len(sr) - (ui_props.wcount * ui_props.hcount)

            if event.value == 'RELEASE':  # Confirm
                ui_props.drag_init = False

                # scroll by a whole page
                if (
                    mx > ui_props.bar_x + ui_props.bar_width - 50
                    and len(sr) - ui_props.scrolloffset > ui_props.wcount * ui_props.hcount
                ):
                    ui_props.scrolloffset = min(
                        ui_props.scrolloffset + (ui_props.wcount * ui_props.hcount),
                        len(sr) - ui_props.wcount * ui_props.hcount,
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
                                self.report({'WARNING'}, "Invalid or library object as input:")
                                target_object = ''
                                target_slot = ''

                # Click interaction
                else:
                    asset_search_index = get_asset_under_mouse(mx, my)

                    if ui_props.asset_type in ('MATERIAL', 'MODEL',):
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

                            asset_data = sr[asset_search_index]
                            bpy.ops.scene.hana3d_download(
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
                            loc = s.cursor.location
                            rotation = s.cursor.rotation_euler

                        bpy.ops.scene.hana3d_download(
                            True,
                            asset_type=ui_props.asset_type,
                            asset_index=asset_search_index,
                            model_location=loc,
                            model_rotation=rotation,
                            target_object=target_object,
                        )

                    else:
                        bpy.ops.scene.hana3d_download(
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
        ui_props = context.window_manager.Hana3DUI

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

        sr = bpy.context.window_manager.get('search results')
        if sr is None:
            bpy.context.window_manager['search results'] = []

        if context.area.type != 'VIEW_3D':
            self.report({'WARNING'}, "View3D not found, cannot run operator")
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

    def execute(self, context):
        return {'RUNNING_MODAL'}


class DefaultNamesOperator(bpy.types.Operator):
    '''Assign default object name as props name and object render job name'''

    bl_idname = "view3d.hana3d_default_name"
    bl_label = "Hana3D Default Name"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    def modal(self, context, event):
        # This is for case of closing the area or changing type:
        ui_props = context.window_manager.Hana3DUI

        if ui_props.turn_off:
            return {'CANCELLED'}

        draw_event = (
            event.type == 'LEFTMOUSE' or event.type == 'RIGHTMOUSE' or event.type == 'ENTER'
        )
        if not draw_event:
            return {'PASS_THROUGH'}

        asset = utils.get_active_asset()
        if asset is None:
            return {'PASS_THROUGH'}

        props = asset.hana3d

        if ui_props.down_up == 'UPLOAD':
            if props.workspace != '' and len(props.tags_list) == 0:
                props.workspace = props.workspace
            if props.name == '' and props.name != asset.name:
                props.name = asset.name
        elif ui_props.down_up == 'SEARCH':
            search_props = utils.get_search_props()
            if (
                search_props.workspace != ''
                and len(search_props.tags_list) == 0
            ):
                search_props.workspace = search_props.workspace

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

    bl_idname = "object.hana3d_data_trasnfer"
    bl_label = "Transfer hana3d data"
    bl_description = "Transfer hana3d metadata from one object to another when fixing uploads with wrong parenting."  # noqa E501
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        source_ob = bpy.context.active_object
        for target_ob in bpy.context.selected_objects:
            if target_ob != source_ob:
                target_ob.property_unset('hana3d')
                for k in source_ob.keys():
                    target_ob[k] = source_ob[k]
        source_ob.property_unset('hana3d')
        return {'FINISHED'}


class UndoWithContext(bpy.types.Operator):
    """Regenerate cobweb"""

    bl_idname = "wm.undo_push_context"
    bl_label = "hana3d undo push"
    bl_description = "hana3d undo push with fixed context"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    # def modal(self, context, event):
    #     return {'RUNNING_MODAL'}

    message: StringProperty('Undo Message', default='hana3d operation')

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

    bl_idname = "object.run_assetbar_fix_context"
    bl_label = "hana3d assetbar with fixed context"
    bl_description = "Run assetbar with fixed context"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    # def modal(self, context, event):
    #     return {'RUNNING_MODAL'}

    def execute(self, context):
        C_dict = bpy.context.copy()
        C_dict.update(region='WINDOW')
        if context.area is None or context.area.type != 'VIEW_3D':
            w, a, r = get_largest_3dview()
            override = {'window': w, 'screen': w.screen, 'area': a, 'region': r}
            C_dict.update(override)
        bpy.ops.view3d.hana3d_asset_bar(
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
    bpy.ops.view3d.hana3d_default_name(C_dict, 'INVOKE_REGION_WIN')


# @persistent
def pre_load(context):
    ui_props = bpy.context.window_manager.Hana3DUI
    ui_props.assetbar_on = False
    ui_props.turn_off = True
    preferences = bpy.context.preferences.addons['hana3d'].preferences
    preferences.login_attempt = False


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
