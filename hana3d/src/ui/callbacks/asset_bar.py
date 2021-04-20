"""Asset bar callbacks."""
import datetime
import math
import os
from contextlib import suppress

import bpy

from .. import bgl_helper
from ...preferences.preferences import Preferences
from ...search import search
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


def draw_tooltip(   # noqa: WPS211
    x,              # noqa: WPS111
    y,              # noqa: WPS111
    text='',
    author='',
    created='',
    revision='',
    img=None,
    gravatar=None,
    sku=None,
):
    """Draw tooltip.

    Parameters:
        x: x-coordinate
        y: y-coordinate
        text: text to be displayed
        author: asset author
        created: asset creation date in epoch
        revision: view revision
        img: image
        gravatar: gravatar
        sku: product sku and lib dict
    """
    region = bpy.context.region
    scale = bpy.context.preferences.view.ui_scale

    ttipmargin = 10
    textmargin = 10

    font_height = int(12 * scale)
    line_height = int(15 * scale)
    nameline_height = int(23 * scale)

    lines = text.split('\n')
    author_lines = author.split('\n')
    ncolumns = 2
    nlines = max(len(lines) - 1, len(author_lines), 2)

    texth = line_height * nlines + nameline_height * 2

    max_dim = max(img.size[0], img.size[1])
    if max_dim == 0:
        return
    isizex = int(512 * scale * img.size[0] / max_dim)
    isizey = int(512 * scale * img.size[1] / max_dim)

    estimated_height = 2 * ttipmargin + textmargin + isizey  # noqa: WPS204

    if estimated_height > y:
        scaledown = y / (estimated_height)
        scale *= scaledown
        # we need to scale these down to have correct size if the tooltip wouldn't fit.
        font_height = int(12 * scale)
        line_height = int(15 * scale)
        nameline_height = int(23 * scale)

        lines = text.split('\n')

        texth = line_height * nlines + nameline_height * 2 + line_height
        isizex = int(512 * scale * img.size[0] / max_dim)
        isizey = int(512 * scale * img.size[1] / max_dim)

    name_height = int(18 * scale)

    x += 2 * ttipmargin  # noqa: WPS111
    y -= 2 * ttipmargin  # noqa: WPS111

    width = isizex + 2 * ttipmargin

    properties_width = 0
    for re in bpy.context.area.regions:
        if re.type == 'UI':
            properties_width = re.width

    x = min(x + width, region.width - properties_width) - width  # noqa: WPS111

    bgcol = bpy.context.preferences.themes[0].user_interface.wcol_tooltip.inner  # noqa: WPS219
    bgcol1 = (bgcol[0], bgcol[1], bgcol[2], 0.6)
    textcol = bpy.context.preferences.themes[0].user_interface.wcol_tooltip.text  # noqa: WPS219
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

    i = 0  # noqa: WPS111
    column_lines = -1  # start minus one for the name
    xtext = x + textmargin
    fsize = name_height
    tcol = textcol

    y_created = (
        y
        - line_height
        - nameline_height
        - ttipmargin
        - textmargin
        - isizey
        + texth
    )
    x_created = xtext + int(isizex / ncolumns)
    created_parsed = (
        datetime.datetime.strptime(created, '%Y-%m-%dT%H:%M:%S.%f')  # noqa: WPS323
        if created else datetime.datetime.utcnow()
    )
    created_date = created_parsed.strftime('%d/%m/%Y - %H:%M:%S')  # noqa: WPS323
    text_created = f'Created: {created_date}'
    bgl_helper.draw_text(text_created, x_created, y_created, font_height, tcol)

    y_revision = y_created - line_height
    x_revision = x_created
    if revision != '0':
        revision_parsed = (
            datetime.datetime.strptime(revision, '%Y-%m-%dT%H:%M:%S')  # noqa: WPS323
            if revision else datetime.datetime.utcnow()
        )
        revision_date = revision_parsed.strftime('%d/%m/%Y - %H:%M:%S')  # noqa: WPS323
        text_revision = f'Modified: {revision_date}'
        bgl_helper.draw_text(text_revision, x_revision, y_revision, font_height, tcol)

    # if it has more than one sku, should add line height foreach one

    y_sku = y_created
    x_sku = x_created
    for sku_id, library in sku.items():
        y_sku += line_height
        text_sku = f'{library} : {sku_id}'
        bgl_helper.draw_text(text_sku, x_sku, y_sku, font_height, tcol)

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
            fsize = font_height
            if line[:4] == 'Tip:':
                tcol = textcol_strong
        i += 1  # noqa: WPS111
        column_lines += 1
        bgl_helper.draw_text(line, xtext, ytext, fsize, tcol)
    xtext += int(isizex / ncolumns)

    column_lines = 1
    for author_line in author_lines:
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
            fsize = font_height
            if author_line[:4] == 'Tip:':
                tcol = textcol_strong
        i += 1  # noqa: WPS111
        column_lines += 1
        bgl_helper.draw_text(author_line, xtext, ytext, fsize, tcol)


def _load_tooltip_thumbnail(search_result: search.AssetData, active_index: int):
    asset_type = search_result.asset_type
    image_name = utils.previmg_name(asset_type, active_index, fullsize=True)
    directory = paths.get_temp_dir(f'{search_result.asset_type}_search')
    thumbnail_path = os.path.join(directory, search_result.thumbnail)

    img = bpy.data.images.get(image_name)
    if img is None or img.filepath != thumbnail_path:
        if os.path.exists(thumbnail_path):
            if img is None:
                img = bpy.data.images.load(thumbnail_path)
                img.name = image_name
            elif img.filepath != thumbnail_path:
                # TODO: replace imgs reloads with a method that forces unpack for thumbs.
                if img.packed_file is not None:
                    img.unpack(method='USE_ORIGINAL')
                img.filepath = thumbnail_path
                img.reload()
                img.name = image_name
        else:
            image_name = utils.previmg_name(asset_type, active_index)
            img = bpy.data.images.get(image_name)
        with suppress(AttributeError):
            img.colorspace_settings.name = 'Linear'

    return img


def _load_tooltip_author(search_result):
    gimg = None
    author_tooltip = ''

    if bpy.context.window_manager.get(f'{HANA3D_NAME}_authors') is not None:
        author = bpy.context.window_manager[f'{HANA3D_NAME}_authors'].get(
            search_result.author_id,
        )
        if author is not None and author != '':
            if author.get('gravatarImg') is not None:
                gimg = utils.get_hidden_image(author['gravatarImg'], author['gravatarHash'])  # noqa: E501
            author_tooltip = author['tooltip']

    return gimg, author_tooltip


def draw_callback2d_search(self, context):
    """Draw search preview.

    Parameters:
        self: Asset Bar Operator
        context: Blender context
    """
    wm = context.window_manager
    ui_props = getattr(wm, HANA3D_UI)
    asset_type = ui_props.asset_type_search.lower()

    hc = (1, 1, 1, 0.07)
    white = (1, 1, 1, 0.2)
    green = (0.2, 1, 0.2, 0.7)
    highlight = bpy.context.preferences.themes[0].user_interface.wcol_menu_item.inner_sel  # noqa: WPS219, E501
    highlight = (1, 1, 1, 0.2)
    # background of asset bar

    sku = {}

    if not ui_props.dragging:
        search_results = search.get_search_results(asset_type)
        len_search = len(search_results)
        original_search_results = search.get_original_search_results()
        if search_results is None:
            return
        h_draw = min(ui_props.hcount, math.ceil(len_search / ui_props.wcount))

        if ui_props.wcount > len_search:
            bar_width = len_search * (ui_props.thumb_size + ui_props.margin) + ui_props.margin
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

        count = ui_props.total_count

        if ui_props.scrolloffset > 0 or count < len_search:
            ui_props.drawoffset = 35
        else:
            ui_props.drawoffset = 0

        if count < len_search:
            page_start = ui_props.scrolloffset + 1
            preferences = Preferences().get()
            page_end = ui_props.scrolloffset + ui_props.wcount * preferences.max_assetbar_rows
            pagination_text = (
                f'{page_start} - {page_end} of {original_search_results["count"]}'
            )

            bgl_helper.draw_text(
                pagination_text,
                ui_props.bar_x + ui_props.bar_width - 125,
                ui_props.bar_y - ui_props.bar_height - 25,
                14,
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
                    bgl_helper.draw_rect(
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

            if original_search_results['count'] - ui_props.scrolloffset > count + 1:
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

        for row in range(0, h_draw):
            w_draw = min(
                ui_props.wcount,
                len_search - row * ui_props.wcount - ui_props.scrolloffset,
            )

            y = ui_props.bar_y - (row + 1) * (row_height)  # noqa: WPS111
            for column in range(0, w_draw):
                x = (  # noqa: WPS111
                    ui_props.bar_x
                    + column * (ui_props.margin + ui_props.thumb_size)
                    + ui_props.margin
                    + ui_props.drawoffset
                )

                index = column + ui_props.scrolloffset + row * ui_props.wcount
                iname = utils.previmg_name(asset_type, index)
                img = bpy.data.images.get(iname)

                if img is None:
                    continue

                max_size = max(img.size[0], img.size[1])
                if max_size == 0:
                    logging.error(f'Image with name {iname} has both sides equal to zero, skipping')
                    continue

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

                else:
                    bgl_helper.draw_rect(x, y, width, height, white)  # noqa: WPS220

                search_result = search_results[index]
                if search_result.downloaded > 0:
                    width = int(width * search_result.downloaded / 100.0)  # noqa: WPS220
                    bgl_helper.draw_rect(x, y - 2, width, 2, green)  # noqa: WPS220

                v_icon = verification_icons[search_result.verification_status]  # noqa: E501
                if v_icon is not None:
                    img = utils.get_thumbnail(v_icon)  # noqa: WPS220
                    bgl_helper.draw_image(  # noqa: WPS220
                        x + ui_props.thumb_size - 26,
                        y + 2,
                        24,
                        24,
                        img,
                        1,
                    )

        if ui_props.draw_tooltip:
            if search_results is not None and -1 < ui_props.active_index < len(search_results):
                search_result = search_results[ui_props.active_index]

                sku.clear()
                for instance in ui_props.sku.keys():
                    sku[ui_props.sku[instance]['name']] = ui_props.sku[instance]['library']

                img = _load_tooltip_thumbnail(search_result, ui_props.active_index)
                if img is not None:

                    gimg, author = _load_tooltip_author(search_result)

                    draw_tooltip(
                        ui_props.mouse_x,
                        ui_props.mouse_y,
                        text=ui_props.tooltip,
                        author=author,
                        created=search_result.created,
                        revision=search_result.revision,
                        img=img,
                        gravatar=gimg,
                        sku=sku,
                    )

    elif ui_props.dragging and (ui_props.draw_drag_image or ui_props.draw_snapped_bounds):
        if ui_props.active_index > -1:
            iname = utils.previmg_name(asset_type, ui_props.active_index)
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
                white,
            )


def draw_callback2d(self, context):
    """Draw asset bar helper functions such as upload preview and asset tooltip.

    Parameters:
        self: Asset bar operator
        context: Blender context
    """
    if not utils.guard_from_crash():
        return

    area = context.area
    try:
        # self.area might throw error just by itself.
        self_area = self.area
        self_window = self.window
        go = True
        if area.spaces[0].region_quadviews:
            if area.spaces[0].region_3d != context.region_data:
                go = False
    except Exception:
        go = False
    if go and area == self_area and context.window == self_window:
        draw_callback2d_search(self, context)


def draw_callback3d(self, context):
    """Draw snapped bbox while dragging and in the future other Hana3D related stuff.

    Parameters:
        self: Asset bar operator
        context: Blender context
    """
    if not utils.guard_from_crash():
        return

    ui = getattr(context.window_manager, HANA3D_UI)

    if ui.asset_type_search.lower() == 'model' and ui.draw_snapped_bounds:
        bgl_helper.draw_bbox(
            ui.snapped_location,
            ui.snapped_rotation,
            ui.snapped_bbox_min,
            ui.snapped_bbox_max,
        )
