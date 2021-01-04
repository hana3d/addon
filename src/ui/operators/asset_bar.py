# flake8: noqa
"""Runs search and displays the asset bar at the same time."""
import logging
import math

import bpy
import mathutils
from bpy.props import BoolProperty, StringProperty
from bpy_extras import view3d_utils
from mathutils import Vector

from ..callbacks.asset_bar import draw_callback_2d, draw_callback_3d
from ..main import UI
from ..preferences.preferences import Preferences
from ...search.search import Search
from ...upload import upload
from .... import search, utils
from ....config import (
    HANA3D_DESCRIPTION,
    HANA3D_MODELS,
    HANA3D_NAME,
    HANA3D_UI,
)
from ....report_tools import execute_wrapper


def get_asset_under_mouse(mousex, mousey):
    ui_props = getattr(bpy.context.window_manager, HANA3D_UI)

    search_object = Search(bpy.context)
    search_results = search_object.results
    if search_results is not None:

        h_draw = min(ui_props.hcount, math.ceil(len(search_results) / ui_props.wcount))
        for b in range(0, h_draw):
            w_draw = min(
                ui_props.wcount,
                len(search_results) - b * ui_props.wcount - ui_props.scrolloffset,
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
        False,
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
    user_preferences = Preferences().get()
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
            math.ceil(len(search_results) / ui.wcount),
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


class AssetBarOperator(bpy.types.Operator):
    """Runs search and displays the asset bar at the same time."""

    bl_idname = f'view3d.{HANA3D_NAME}_asset_bar'
    bl_label = f'{HANA3D_DESCRIPTION} Asset Bar UI'
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    do_search: BoolProperty(  # type: ignore
        name='Run Search',
        description='',
        default=True,
        options={'SKIP_SAVE'},
    )

    keep_running: BoolProperty(  # type: ignore
        name='Keep Running',
        description='',
        default=True,
        options={'SKIP_SAVE'},
    )

    tooltip: StringProperty(  # type: ignore
        default='runs search and displays the asset bar at the same time',
    )

    @classmethod
    def description(cls, context, properties):  # noqa: D102
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
                    props = upload.get_upload_props()
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
        if len(search_results) - ui_props.scrolloffset < (ui_props.wcount * ui_props.hcount) + 10:  # noqa: WPS221,WPS204
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
                and len(search_results) - ui_props.scrolloffset > (ui_props.wcount * ui_props.hcount)  # noqa: E501
            ):
                if ui_props.hcount > 1:
                    ui_props.scrolloffset += ui_props.wcount
                else:
                    ui_props.scrolloffset += 1
                if len(search_results) - ui_props.scrolloffset < (ui_props.wcount * ui_props.hcount):  # noqa: N400
                    ui_props.scrolloffset = len(search_results) - (ui_props.wcount * ui_props.hcount)  # noqa: E501

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
                bpy.context.window.cursor_set('DEFAULT')
                return {'PASS_THROUGH'}

            search_object = Search(bpy.context)
            search_results = search_object.results

            if not ui_props.dragging:
                bpy.context.window.cursor_set('DEFAULT')

                if (  # noqa: WPS337
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
                    if ui_props.active_index < len(search_results) and ui_props.active_index > -1:  # noqa: WPS333
                        ui_props.draw_snapped_bounds = True  # noqa: WPS220
                        active_mod = search_results[ui_props.active_index]  # noqa: WPS220
                        ui_props.snapped_bbox_min = Vector(active_mod['bbox_min'])  # noqa: WPS220
                        ui_props.snapped_bbox_max = Vector(active_mod['bbox_max'])  # noqa: WPS220

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
                    bpy.context.window.cursor_set('NONE')
                    ui_props.draw_tooltip = False
                    ui_props.drag_length = 0
                elif ui_props.asset_type == 'SCENE':
                    ui_props.drag_init = True
                    bpy.context.window.cursor_set('NONE')
                    ui_props.draw_tooltip = False
                    ui_props.drag_length = 0

            if not ui_props.dragging and not mouse_in_asset_bar(mx, my):
                return {'PASS_THROUGH'}

            # this can happen by switching result asset types - length of search result changes
            if (
                ui_props.scrolloffset > 0
                and (ui_props.wcount * ui_props.hcount) > len(search_results) - ui_props.scrolloffset  # noqa: E501
            ):
                ui_props.scrolloffset = len(search_results) - (ui_props.wcount * ui_props.hcount)  # noqa: E501

            if event.value == 'RELEASE':  # Confirm
                ui_props.drag_init = False

                # scroll by a whole page
                if (
                    mx > ui_props.bar_x + ui_props.bar_width - 50  # noqa: WPS432
                    and len(search_results) - ui_props.scrolloffset > ui_props.wcount * ui_props.hcount  # noqa: E501
                ):
                    ui_props.scrolloffset = min(
                        ui_props.scrolloffset + (ui_props.wcount * ui_props.hcount),
                        len(search_results) - ui_props.wcount * ui_props.hcount,
                    )
                    return {'RUNNING_MODAL'}
                if mx < ui_props.bar_x + 50 and ui_props.scrolloffset > 0:
                    ui_props.scrolloffset = max(
                        0,
                        ui_props.scrolloffset - ui_props.wcount * ui_props.hcount,
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
                                location=(event.mouse_region_x, event.mouse_region_y),
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
                                logging.warning('Invalid or library object as input:')  # noqa: WPS220
                                target_object = ''
                                target_slot = ''

                # Click interaction
                else:
                    asset_search_index = get_asset_under_mouse(mx, my)

                    if ui_props.asset_type in ('MATERIAL', 'MODEL'):  # noqa: WPS220
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

                            asset_data = search_results[asset_search_index]  # noqa: WPS220
                            download_op = getattr(bpy.ops.scene, f'{HANA3D_NAME}_download')  # noqa: WPS220
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
                            loc = scene.cursor.location  # noqa: WPS220
                            rotation = scene.cursor.rotation_euler  # noqa: WPS220

                        download_op = getattr(bpy.ops.scene, HANA3D_NAME + '_download')
                        download_op(
                            True,
                            asset_type=ui_props.asset_type,
                            asset_index=asset_search_index,
                            model_location=loc,
                            model_rotation=rotation,
                            target_object=target_object,
                        )

                    else:
                        download_op = getattr(bpy.ops.scene, HANA3D_NAME + '_download')
                        download_op(
                            asset_type=ui_props.asset_type,
                            asset_index=asset_search_index,
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
            search_object.results = []  # noqa: WPS110

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

        ui = UI()
        ui.active_window = self.window
        ui.active_area = self.area
        ui.active_region = self.region

        update_ui_size(self.area, self.region)

        self._handle_2d = bpy.types.SpaceView3D.draw_handler_add(
            draw_callback_2d,
            args,
            'WINDOW',
            'POST_PIXEL',
        )
        self._handle_3d = bpy.types.SpaceView3D.draw_handler_add(
            draw_callback_3d,
            args,
            'WINDOW',
            'POST_VIEW',
        )

        context.window_manager.modal_handler_add(self)
        ui_props.assetbar_on = True
        return {'RUNNING_MODAL'}

    @execute_wrapper
    def execute(self, context):
        return {'RUNNING_MODAL'}
