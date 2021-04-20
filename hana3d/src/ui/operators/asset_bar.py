"""Runs search and displays the asset bar at the same time."""
import logging
import math

import bpy
import mathutils
from bpy.props import BoolProperty, StringProperty
from bpy_extras import view3d_utils
from mathutils import Vector

from ..callbacks.asset_bar import draw_callback2d, draw_callback3d
from ..main import UI
from ...asset.asset_type import AssetType
from ...edit_asset.edit import set_edit_props
from ...preferences.preferences import Preferences
from ...search import search
from ...upload import upload
from .... import utils
from ....config import (
    HANA3D_DESCRIPTION,
    HANA3D_MODELS,
    HANA3D_NAME,
    HANA3D_UI,
)
from ....report_tools import execute_wrapper

NO_ASSET = -3


def get_asset_under_mouse(mousex: float, mousey: float) -> int:
    """Return the asset under the mouse.

    Parameters:
        mousex: mouse x-coordinate
        mousey: mouse y-coordinate

    Returns:
        int: index of the asset under the mouse
    """
    ui_props = getattr(bpy.context.window_manager, HANA3D_UI)
    search_results = search.get_search_results()
    len_search = len(search_results)
    if search_results is not None:
        h_draw = min(ui_props.hcount, math.ceil(len_search / ui_props.wcount))
        for row in range(0, h_draw):
            w_draw = min(
                ui_props.wcount, len_search - row * ui_props.wcount - ui_props.scrolloffset,
            )
            for column in range(0, w_draw):
                x = (  # noqa: WPS111
                    ui_props.bar_x
                    + column * (ui_props.margin + ui_props.thumb_size)
                    + ui_props.margin
                    + ui_props.drawoffset
                )
                y = (  # noqa: WPS111
                    ui_props.bar_y
                    - ui_props.margin
                    - (ui_props.thumb_size + ui_props.margin) * (row + 1)
                )
                width = ui_props.thumb_size
                height = ui_props.thumb_size

                if x < mousex < x + width and y < mousey < y + height:
                    return column + ui_props.wcount * row + ui_props.scrolloffset

    return NO_ASSET


def mouse_raycast(context: bpy.types.Context, mx: float, my: float) -> tuple:
    """Perform a raycast from the mouse.

    Parameters:
        context: Blender context
        mx: mouse x-coordinate
        my: mouse y-coordinate

    Returns:
        tuple: Tuple containing: if a object was hit; location; normal; rotation;
        face index; object; matrix;
    """
    region = context.region
    rv3d = context.region_data
    coord = mx, my

    # get the ray from the viewport and mouse
    target_distance = 1e9
    view_vector = view3d_utils.region_2d_to_vector_3d(region, rv3d, coord)
    ray_origin = view3d_utils.region_2d_to_origin_3d(region, rv3d, coord)
    ray_target = ray_origin + (view_vector * target_distance)

    vec = ray_target - ray_origin

    (
        has_hit,
        snapped_location,
        snapped_normal,
        face_index,
        obj_hit,
        matrix,
    ) = bpy.context.scene.ray_cast(bpy.context.view_layer.depsgraph, ray_origin, vec)

    randoffset = math.pi
    if has_hit:
        snapped_rotation = snapped_normal.to_track_quat('Z', 'Y').to_euler()
        up = Vector((0, 0, 1))
        props = getattr(bpy.context.window_manager, HANA3D_MODELS)
        angle_threshold = 10.0
        if snapped_normal.angle(up) < math.radians(angle_threshold):
            randoffset = props.offset_rotation_amount + math.pi
        else:
            # we don't rotate this way on walls and ceilings.
            randoffset = props.offset_rotation_amount

    else:
        snapped_rotation = mathutils.Quaternion((0, 0, 0, 0)).to_euler()

    snapped_rotation.rotate_axis('Z', randoffset)

    return has_hit, snapped_location, snapped_normal, snapped_rotation, face_index, obj_hit, matrix


def floor_raycast(context: bpy.types.Context, mx: float, my: float) -> tuple:
    """Perform a raycast from the floor.

    Parameters:
        context: Blender context
        mx: mouse x-coordinate
        my: mouse y-coordinate

    Returns:
        tuple: Tuple containing: if a object was hit; location; normal; rotation;
        face index; object; matrix;
    """
    region = context.region
    rv3d = context.region_data
    coord = mx, my

    # get the ray from the viewport and mouse
    view_vector = view3d_utils.region_2d_to_vector_3d(region, rv3d, coord)
    ray_origin = view3d_utils.region_2d_to_origin_3d(region, rv3d, coord)
    ray_target = ray_origin + (view_vector * 1000)

    # various intersection plane normals are needed for corner cases
    # that might actually happen quite often - in front and side view.
    # default plane normal is scene floor.
    tolerance = 1e-4
    plane_normal = (0, 0, 1)
    if math.isclose(view_vector.z, 0, abs_tol=tolerance):
        if math.isclose(view_vector.x, 0, abs_tol=tolerance):
            plane_normal = (0, 1, 0)
        else:
            plane_normal = (1, 0, 0)

    origin = (0, 0, 0)
    snapped_location = mathutils.geometry.intersect_line_plane(
        ray_origin, ray_target, origin, plane_normal,
    )
    if snapped_location is not None:
        has_hit = True
        snapped_normal = Vector((0, 0, 1))
        face_index = None
        obj_hit = None
        matrix = None
        snapped_rotation = snapped_normal.to_track_quat('Z', 'Y').to_euler()
        props = getattr(bpy.context.window_manager, HANA3D_MODELS)
        randoffset = props.offset_rotation_amount + math.pi
        snapped_rotation.rotate_axis('Z', randoffset)

    return has_hit, snapped_location, snapped_normal, snapped_rotation, face_index, obj_hit, matrix


def mouse_in_asset_bar(mx: float, my: float) -> bool:
    """Return whether the mouse is or is not in the asset bar.

    Parameters:
        mx: mouse x-coordinate
        my: mouse y-coordinate

    Returns:
        bool: True if the mouse is in the asset bar, False otherwise
    """
    ui_props = getattr(bpy.context.window_manager, HANA3D_UI)

    return (
        ui_props.bar_y - ui_props.bar_height < my < ui_props.bar_y
        and ui_props.bar_x < mx < ui_props.bar_x + ui_props.bar_width
    )


def mouse_in_region(region: bpy.types.Region, mx: float, my: float) -> bool:
    """Return whether the mouse is or is not in the region.

    Parameters:
        region: Blender region
        mx: mouse x-coordinate
        my: mouse y-coordinate

    Returns:
        bool: True if the mouse is in the region, False otherwise
    """
    return 0 < my < region.height and 0 < mx < region.width


def update_ui_size(area: bpy.types.Area, region: bpy.types.Region) -> None:
    """Update ui size.

    Parameters:
        area: Blender area
        region: Blender region
    """
    wm = bpy.context.window_manager
    ui = getattr(wm, HANA3D_UI)
    user_preferences = Preferences().get()
    ui_scale = bpy.context.preferences.view.ui_scale

    ui.margin = ui.bl_rna.properties['margin'].default * ui_scale
    ui.thumb_size = user_preferences.thumb_size * ui_scale

    reg_multiplier = 1
    if not bpy.context.preferences.system.use_region_overlap:
        reg_multiplier = 0

    for re in area.regions:
        if re.type == 'TOOLS':
            ui.bar_x = re.width * reg_multiplier + ui.margin + ui.bar_x_offset * ui_scale
        elif re.type == 'UI':
            ui.bar_end = re.width * reg_multiplier + 100 * ui_scale

    ui.bar_width = region.width - ui.bar_x - ui.bar_end
    ui.wcount = math.floor((ui.bar_width - 2 * ui.drawoffset) / (ui.thumb_size + ui.margin))

    search_results = search.get_search_results()
    if search_results is not None and ui.wcount > 0:
        ui.hcount = min(
            user_preferences.max_assetbar_rows,
            math.ceil(len(search_results) / ui.wcount),
        )
    else:
        ui.hcount = 1
    ui.total_count = ui.wcount * ui.hcount
    ui.bar_height = (ui.thumb_size + ui.margin) * ui.hcount + ui.margin
    ui.bar_y = region.height - ui.bar_y_offset * ui_scale
    if ui.assetbar_on:
        ui.reports_y = ui.bar_y - ui.bar_height - 100
        ui.reports_x = ui.bar_x
    else:
        ui.reports_y = ui.bar_y - 600
        ui.reports_x = ui.bar_x


class AssetBarOperator(bpy.types.Operator):  # noqa: WPS338, WPS214
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

    def search_more(self, asset_type: AssetType):
        """Search more results."""
        original_search_results = search.get_original_search_results(asset_type)
        if original_search_results is not None and original_search_results.get('next') is not None:
            len_search = len(search.get_search_results())
            image_name = utils.previmg_name(asset_type, len_search - 1)
            img = bpy.data.images.get(image_name)
            if img:
                logging.debug(f'{image_name} has already loaded, will continue search')
                search.run_operator(get_next=True)

    def exit_modal(self):
        """Exit modal."""
        try:
            bpy.types.SpaceView3D.draw_handler_remove(self._handle2d, 'WINDOW')
            bpy.types.SpaceView3D.draw_handler_remove(self._handle3d, 'WINDOW')
        except Exception:
            logging.info('Could not remove draw handlers')
        ui_props = getattr(bpy.context.window_manager, HANA3D_UI)

        ui_props.dragging = False
        ui_props.tooltip = ''
        ui_props.active_index = NO_ASSET
        ui_props.draw_drag_image = False
        ui_props.draw_snapped_bounds = False
        ui_props.has_hit = False
        ui_props.assetbar_on = False

    def _generate_tooltip(self, event, ui_props):
        ui_props.draw_tooltip = True

        mouse_event = event.type in {'LEFTMOUSE', 'RIGHTMOUSE'} and event.value == 'RELEASE'
        if mouse_event or event.type == 'ENTER' or ui_props.tooltip == '':
            active_obj = bpy.context.active_object

            if active_obj is None:
                return

            model = ui_props.asset_type_search == 'MODEL'
            if active_obj.active_material is not None:
                material = ui_props.asset_type_search == 'MATERIAL'
            if model or material:
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

    def _raycast_update_props(self, ui_props, context, mx, my):
        raycast = mouse_raycast(context, mx, my)
        has_hit, *_ = raycast

        # MODELS can be dragged on scene floor
        if not has_hit and ui_props.asset_type_search == 'MODEL':
            raycast = floor_raycast(context, mx, my)

        ui_props.has_hit = raycast[0]
        ui_props.snapped_location = raycast[1]
        ui_props.snapped_normal = raycast[2]
        ui_props.snapped_rotation = raycast[3]

        return raycast

    def modal(self, context, event):  # noqa: D102, WPS344, WPS212
        # This is for case of closing the area or changing type:
        ui_props = getattr(context.window_manager, HANA3D_UI)
        areas = []

        if bpy.context.scene != self.scene:
            self.exit_modal()
            return {'CANCELLED'}

        for window in context.window_manager.windows:
            areas.extend(window.screen.areas)

        if (  # noqa: WPS337
            self.area not in areas
            or self.area.type != 'VIEW_3D'
            or self.has_quad_views != bool(self.area.spaces[0].region_quadviews)
        ):
            # logging.info('search areas')   bpy.context.area.spaces[0].region_quadviews
            # stopping here model by now - because of:
            #   switching layouts or maximizing area now fails to assign new area throwing the bug
            #   internal error: modal gizmo-map handler has invalid area
            self.exit_modal()
            return {'CANCELLED'}

        update_ui_size(self.area, self.region)

        # this was here to check if sculpt stroke is running, but obviously that didn't help,
        # since the RELEASE event is cought by operator and thus
        # there is no way to detect a stroke has ended...
        if bpy.context.mode in {'SCULPT', 'PAINT_TEXTURE'}:
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
            return {'PASS_THROUGH'}  # noqa: WPS204

        # TODO add one more condition here to take less performance.
        scene = bpy.context.scene
        search_results = search.get_search_results()
        # If there aren't any results, we need no interaction(yet)
        if search_results is None:
            return {'PASS_THROUGH'}
        len_search = len(search_results)
        if ui_props.scrolloffset > len_search:
            ui_props.scrolloffset = 0
        elif len_search - ui_props.scrolloffset < ui_props.total_count + 10:  # noqa: WPS221,WPS204
            asset_type = ui_props.asset_type_search.lower()
            self.search_more(asset_type)
        if event.type in {'WHEELUPMOUSE', 'WHEELDOWNMOUSE', 'TRACKPADPAN'}:
            # scrolling
            mx = event.mouse_region_x
            my = event.mouse_region_y

            if ui_props.dragging and not mouse_in_asset_bar(mx, my):
                sprops = getattr(context.window_manager, HANA3D_MODELS)
                if event.type == 'WHEELUPMOUSE':
                    sprops.offset_rotation_amount += sprops.offset_rotation_step
                elif event.type == 'WHEELDOWNMOUSE':
                    sprops.offset_rotation_amount -= sprops.offset_rotation_step

                self._raycast_update_props(ui_props, context, mx, my)

                return {'RUNNING_MODAL'}  # noqa: WPS204

            if not mouse_in_asset_bar(mx, my):
                return {'PASS_THROUGH'}

            if event.type == 'WHEELDOWNMOUSE' and len_search - ui_props.scrolloffset > ui_props.total_count:  # noqa: E501
                if ui_props.hcount > 1:
                    ui_props.scrolloffset += ui_props.wcount
                else:
                    ui_props.scrolloffset += 1
                if len_search - ui_props.scrolloffset < ui_props.total_count:
                    ui_props.scrolloffset = len_search - ui_props.total_count

            if event.type == 'WHEELUPMOUSE' and ui_props.scrolloffset > 0:  # noqa: WPS204
                if ui_props.hcount > 1:
                    ui_props.scrolloffset -= ui_props.wcount
                else:
                    ui_props.scrolloffset -= 1
                if ui_props.scrolloffset < 0:
                    ui_props.scrolloffset = 0

            return {'RUNNING_MODAL'}
        if event.type == 'MOUSEMOVE':  # Apply

            region = self.region
            mx = event.mouse_region_x
            my = event.mouse_region_y

            ui_props.mouse_x = mx
            ui_props.mouse_y = my

            mouse_dragging_in_region = ui_props.dragging and mouse_in_region(region, mx, my)

            if ui_props.drag_init:
                ui_props.drag_length += 1
                if ui_props.drag_length > 2:
                    ui_props.dragging = True
                    ui_props.drag_init = False

            elif not mouse_dragging_in_region and not mouse_in_asset_bar(mx, my):
                ui_props.dragging = False
                ui_props.has_hit = False
                ui_props.active_index = NO_ASSET
                ui_props.draw_drag_image = False
                ui_props.draw_snapped_bounds = False
                ui_props.draw_tooltip = False
                bpy.context.window.cursor_set('DEFAULT')
                return {'PASS_THROUGH'}

            search_results = search.get_search_results()
            original_search_results = search.get_original_search_results()
            len_search = len(search_results)

            if not ui_props.dragging and not ui_props.drag_init:
                bpy.context.window.cursor_set('DEFAULT')

                if search_results is not None and ui_props.total_count > len_search:
                    if ui_props.scrolloffset > 0:
                        ui_props.scrolloffset = 0

                asset_search_index = get_asset_under_mouse(mx, my)
                ui_props.active_index = asset_search_index
                if asset_search_index > -1:
                    asset_data = search_results[asset_search_index]

                    ui_props.sku.clear()

                    for library in asset_data.libraries:
                        sku = ui_props.sku.add()
                        sku['name'] = library['metadata']['view_props']['sku'] or ''
                        sku['library'] = library['name'] or ''

                    ui_props.draw_tooltip = True
                    ui_props.tooltip = asset_data.tooltip

                else:
                    ui_props.draw_tooltip = False

                if mx > ui_props.bar_x + ui_props.bar_width - 50:
                    if original_search_results['count'] - ui_props.scrolloffset > ui_props.total_count + 1:  # noqa: E501
                        ui_props.active_index = -1
                        return {'RUNNING_MODAL'}
                if mx < ui_props.bar_x + 50 and ui_props.scrolloffset > 0:
                    ui_props.active_index = -2
                    return {'RUNNING_MODAL'}

            elif ui_props.dragging and mouse_in_region(region, mx, my):
                self._raycast_update_props(ui_props, context, mx, my)

            if ui_props.has_hit and ui_props.asset_type_search == 'MODEL':
                # this condition is here to fix a bug for a scene
                # submitted by a user, so this situation shouldn't
                # happen anymore, but there might exists scenes
                # which have this problem for some reason.
                if -1 < ui_props.active_index < len_search:
                    ui_props.draw_snapped_bounds = True  # noqa: WPS220
                    active_mod = search_results[ui_props.active_index]  # noqa: WPS220
                    ui_props.snapped_bbox_min = Vector(active_mod.bbox_min)  # noqa: WPS220
                    ui_props.snapped_bbox_max = Vector(active_mod.bbox_max)  # noqa: WPS220

            else:
                ui_props.draw_snapped_bounds = False
                ui_props.draw_drag_image = True

            return {'RUNNING_MODAL'}

        if event.type == 'RIGHTMOUSE':
            region = self.region
            mx = event.mouse_x - region.x
            my = event.mouse_y - region.y

        if event.type == 'LEFTMOUSE':
            region = self.region
            mx = event.mouse_x - region.x
            my = event.mouse_y - region.y

            ui_props = getattr(context.window_manager, HANA3D_UI)
            if event.value == 'PRESS' and ui_props.active_index > -1:
                if ui_props.asset_type_search in {'MODEL', 'MATERIAL'}:
                    # check if asset is locked and let the user know in that case
                    asset_search_index = ui_props.active_index
                    asset_data = search_results[asset_search_index]
                    # go on with drag init
                    ui_props.drag_init = True
                    bpy.context.window.cursor_set('NONE')
                    ui_props.draw_tooltip = False
                    ui_props.drag_length = 0
                elif ui_props.asset_type_search == 'SCENE':
                    ui_props.drag_init = True
                    bpy.context.window.cursor_set('NONE')
                    ui_props.draw_tooltip = False
                    ui_props.drag_length = 0

            if not ui_props.dragging and not mouse_in_asset_bar(mx, my):
                return {'PASS_THROUGH'}

            # this can happen by switching result asset types - length of search result changes
            if ui_props.scrolloffset > 0 and ui_props.total_count > len_search - ui_props.scrolloffset:  # noqa: E501
                ui_props.scrolloffset = len_search - ui_props.total_count  # noqa: E501

            if event.value == 'RELEASE':  # Confirm
                ui_props.drag_init = False

                # scroll by a whole page
                if mx > ui_props.bar_x + ui_props.bar_width - 50:
                    if len_search - ui_props.scrolloffset > ui_props.total_count:
                        ui_props.scrolloffset = min(
                            ui_props.scrolloffset + ui_props.total_count,
                            len_search - ui_props.total_count,
                        )
                        return {'RUNNING_MODAL'}
                if mx < ui_props.bar_x + 50 and ui_props.scrolloffset > 0:
                    ui_props.scrolloffset = max(
                        0,
                        ui_props.scrolloffset - ui_props.total_count,
                    )
                    return {'RUNNING_MODAL'}

                # Drag-drop interaction
                if ui_props.dragging and mouse_in_region(region, mx, my):
                    asset_search_index = ui_props.active_index
                    # raycast here
                    ui_props.active_index = NO_ASSET

                    if ui_props.asset_type_search == 'MODEL':
                        raycast = self._raycast_update_props(ui_props, context, mx, my)

                        if not ui_props.has_hit:
                            return {'RUNNING_MODAL'}

                        obj_hit = raycast[5]
                        target_object = ''
                        if obj_hit is not None:
                            target_object = obj_hit.name
                        target_slot = ''

                    elif ui_props.asset_type_search == 'MATERIAL':
                        raycast = mouse_raycast(context, mx, my)

                        ui_props.has_hit = raycast[0]
                        ui_props.snapped_location = raycast[1]
                        ui_props.snapped_normal = raycast[2]
                        ui_props.snapped_rotation = raycast[3]
                        face_index = raycast[4]
                        obj_hit = raycast[5]

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
                                obj_hit = sel1[0]
                                target_slot = sel1[0].active_material_index
                                ui_props.has_hit = True
                            utils.selection_set(sel)

                        if not ui_props.has_hit:
                            return {'RUNNING_MODAL'}

                        # first, test if object can have material applied.
                        # TODO add other types here if droppable.
                        if obj_hit is not None and not obj_hit.is_library_indirect and obj_hit.type == 'MESH':  # noqa: E501
                            target_object = obj_hit.name
                            # create final mesh to extract correct material slot
                            depsgraph = bpy.context.evaluated_depsgraph_get()
                            object_eval = obj_hit.evaluated_get(depsgraph)
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
                    if asset_search_index > NO_ASSET:
                        bpy.context.view_layer.objects.active = None
                        set_edit_props(asset_search_index)

                    return {'RUNNING_MODAL'}

                # FIRST START SEARCH

                if asset_search_index == NO_ASSET:
                    return {'RUNNING_MODAL'}
                if asset_search_index > NO_ASSET:
                    if ui_props.asset_type_search == 'MATERIAL':
                        if target_object != '':
                            # position is for downloader:
                            loc = ui_props.snapped_location
                            rotation = (0, 0, 0)

                            asset_data = search_results[asset_search_index]
                            download_op = getattr(bpy.ops.scene, f'{HANA3D_NAME}_download')
                            download_op(
                                True,  # noqa: WPS425
                                asset_type=ui_props.asset_type_search,
                                asset_index=asset_search_index,
                                model_location=loc,
                                model_rotation=rotation,
                                target_object=target_object,
                                material_target_slot=target_slot,
                            )

                    elif ui_props.asset_type_search == 'MODEL':
                        if ui_props.has_hit and ui_props.dragging:
                            loc = ui_props.snapped_location
                            rotation = ui_props.snapped_rotation
                        else:
                            loc = scene.cursor.location  # noqa: WPS220
                            rotation = scene.cursor.rotation_euler  # noqa: WPS220

                        download_op = getattr(bpy.ops.scene, f'{HANA3D_NAME}_download')
                        download_op(
                            True,  # noqa: WPS425
                            asset_type=ui_props.asset_type_search,
                            asset_index=asset_search_index,
                            model_location=loc,
                            model_rotation=rotation,
                            target_object=target_object,
                        )

                    else:
                        download_op = getattr(bpy.ops.scene, f'{HANA3D_NAME}_download')
                        download_op(
                            asset_type=ui_props.asset_type_search,
                            asset_index=asset_search_index,
                        )

                    ui_props.dragging = False
                    return {'RUNNING_MODAL'}
            else:
                return {'RUNNING_MODAL'}
        return {'PASS_THROUGH'}

    def invoke(self, context, event):  # noqa: D102
        # FIRST START SEARCH
        ui_props = getattr(context.window_manager, HANA3D_UI)

        if self.do_search:
            ui_props.scrolloffset = 0
            search.run_operator()

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

            return {'FINISHED'}

        ui_props.dragging = False  # only for cases where assetbar ended with an error.
        ui_props.assetbar_on = True
        ui_props.turn_off = False

        if context.area.type != 'VIEW_3D':
            logging.warning('View3D not found, cannot run operator')
            return {'CANCELLED'}

        # the arguments we pass the the callback
        args = (self, context)

        self.window = context.window
        self.area = context.area
        self.scene = bpy.context.scene

        self.has_quad_views = bool(bpy.context.area.spaces[0].region_quadviews)  # noqa: WPS219

        for region in self.area.regions:
            if region.type == 'WINDOW':
                self.region = region

        ui = UI()
        ui.active_window = self.window
        ui.active_area = self.area
        ui.active_region = self.region

        update_ui_size(self.area, self.region)

        self._handle2d = bpy.types.SpaceView3D.draw_handler_add(
            draw_callback2d,
            args,
            'WINDOW',
            'POST_PIXEL',
        )
        self._handle3d = bpy.types.SpaceView3D.draw_handler_add(
            draw_callback3d,
            args,
            'WINDOW',
            'POST_VIEW',
        )

        context.window_manager.modal_handler_add(self)
        ui_props.assetbar_on = True
        return {'RUNNING_MODAL'}

    @execute_wrapper
    def execute(self, context):  # noqa: D102
        return {'RUNNING_MODAL'}
