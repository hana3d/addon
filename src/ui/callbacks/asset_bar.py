# flake8: noqa
"""Asset bar callbacks."""
import math
import os

import bpy

from .. import bgl_helper
from ...preferences.preferences import Preferences
from ...search.search import Search
from .... import paths, utils
from ....config import HANA3D_NAME, HANA3D_UI

verification_icons = {
    'ready': 'vs_ready.png',
    'deleted': 'vs_deleted.png',
    'uploaded': 'vs_uploaded.png',
    'uploading': 'vs_uploading.png',
    'on_hold': 'vs_on_hold.png',
    'validated': None,
    'rejected': 'vs_rejected.png',
}


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
                    f'{page_start} - {page_end} of {search_object.results_orig["count"]}'  # noqa: E501
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

            # if user_preferences.api_key == '':
            #     report = 'Register on Hana3D website to upload your own assets.'
            #     ui_bgl.draw_text(report, ui_props.bar_x + ui_props.margin,
            #                      ui_props.bar_y - 25 - ui_props.margin - ui_props.bar_height, 15)
            # elif len(search_results) == 0:
            #     report = 'Hana3D - No matching results found.'
            #     ui_bgl.draw_text(report, ui_props.bar_x + ui_props.margin,
            #                      ui_props.bar_y - 25 - ui_props.margin, 15)
        # if props.report != '' and props.is_searching or props.search_error:
        #     ui_bgl.draw_text(props.report, ui_props.bar_x,
        #                      ui_props.bar_y - 15 - ui_props.margin - ui_props.bar_height, 15)

        props = getattr(wm, HANA3D_UI)
        if props.draw_tooltip:
            # TODO move this lazy loading into a function and don't duplicate through the code
            iname = utils.previmg_name(ui_props.active_index, fullsize=True)

            directory = paths.get_temp_dir(f'{props.asset_type.lower()}_search')
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
                    a = bpy.context.window_manager[f'{HANA3D_NAME}_authors'].get(  # noqa: WPS111,WPS440
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


def draw_callback_3d(self, context):
    """Draw snapped bbox while dragging and in the future other Hana3D related stuff."""
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
