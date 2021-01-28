"""Upload Panel."""
import bpy
from bpy.types import Panel

from ...config import HANA3D_DESCRIPTION, HANA3D_NAME, HANA3D_UI
from ..unified_props import Unified
from ..upload import upload
from .lib import draw_selected_libraries, draw_selected_tags, label_multiline


class Hana3DUploadPanel(Panel):  # noqa: WPS214
    """Upload Panel."""

    bl_category = HANA3D_DESCRIPTION
    bl_idname = f'VIEW3D_PT_{HANA3D_NAME}_upload'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_label = f'Upload Assets to {HANA3D_DESCRIPTION}'

    @classmethod
    def poll(cls, context):  # noqa: D102
        return True

    def draw(self, context):  # noqa: D102,WPS210,WPS213
        scene = context.scene
        ui_props = getattr(context.window_manager, HANA3D_UI)
        layout = self.layout
        layout.prop(ui_props, 'asset_type_upload', expand=False, text='')

        if ui_props.assetbar_on:
            text = 'Hide asset preview - ;'
        else:
            text = 'Show asset preview - ;'
        op = layout.operator(f'view3d.{HANA3D_NAME}_asset_bar', text=text, icon='EXPORT')
        op.keep_running = False
        op.do_search = False
        op.tooltip = 'Show/Hide asset preview'

        engine = scene.render.engine
        if engine not in {'CYCLES', 'BLENDER_EEVEE'}:
            rtext = (
                'Only Cycles and EEVEE render engines are currently supported. '
                + f'Please use Cycles for all assets you upload to {HANA3D_DESCRIPTION}.'
            )
            label_multiline(layout, rtext, icon='ERROR')
            return

        if ui_props.asset_type_upload == 'MODEL':
            if bpy.context.view_layer.objects.active is not None:
                self._draw_panel_common_upload(context)
            else:
                layout.label(text='select object to upload')
        elif ui_props.asset_type_upload == 'SCENE':
            self._draw_panel_common_upload(context)
        elif ui_props.asset_type_upload == 'MATERIAL':
            active_object = bpy.context.view_layer.objects.active is not None
            active_material = getattr(bpy.context.active_object,
                                      'active_material', None) is not None
            if active_object and active_material:
                self._draw_panel_common_upload(context)
            else:
                label_multiline(layout, text='select object with material to upload materials')

    def _prop_needed(self, layout, props, name, value, is_not_filled=''):  # noqa: WPS211,WPS110
        row = layout.row()
        if value == is_not_filled:
            row.alert = True
            row.prop(props, name)
            row.alert = False
        else:
            row.prop(props, name)
        return row

    def _draw_panel_common_upload(self, context):  # noqa: WPS210,WPS213
        layout = self.layout
        uiprops = getattr(bpy.context.window_manager, HANA3D_UI)
        asset_type = uiprops.asset_type_upload
        props = upload.get_upload_props()
        unified_props = Unified(context).props

        box = layout.box()
        box.label(text='Workspace and Lib', icon='ASSET_MANAGER')
        box.prop(unified_props, 'workspace', expand=False, text='Workspace')
        row = box.row()
        row.prop_search(props, 'libraries_input', props, 'libraries_list', icon='VIEWZOOM')
        row.operator(f'object.{HANA3D_NAME}_refresh_libraries', text='', icon='FILE_REFRESH')
        draw_selected_libraries(box, props, f'object.{HANA3D_NAME}_remove_library_upload')
        for name in props.custom_props.keys():
            box.prop(props.custom_props, f'["{name}"]')

        box = layout.box()
        box.label(text='Asset Info', icon='MESH_CUBE')
        row = self._prop_needed(box, props, 'name', props.name)
        row.operator(f'object.{HANA3D_NAME}_share_asset', text='', icon='LINKED')
        box.prop(props, 'description')
        col = box.column()
        if props.is_generating_thumbnail:
            col.enabled = False
        row = col.row(align=True)
        self._prop_needed(row, props, 'thumbnail', props.has_thumbnail, is_not_filled=False)
        if bpy.context.scene.render.engine in {'CYCLES', 'BLENDER_EEVEE'}:
            if asset_type == 'MODEL':
                row.operator(f'object.{HANA3D_NAME}_thumbnail', text='', icon='IMAGE_DATA')
            elif asset_type == 'SCENE':
                row.operator(f'scene.{HANA3D_NAME}_thumbnail', text='', icon='IMAGE_DATA')
            elif asset_type == 'MATERIAL':
                row.operator(f'material.{HANA3D_NAME}_thumbnail', text='', icon='IMAGE_DATA')
        if props.is_generating_thumbnail or props.thumbnail_generating_state != '':
            row = box.row()
            row.label(text=props.thumbnail_generating_state)
            if props.is_generating_thumbnail:
                op = row.operator(f'object.{HANA3D_NAME}_kill_bg_process', text='', icon='CANCEL')
                op.process_source = asset_type
                op.process_type = 'THUMBNAILER'

        box = layout.box()
        box.label(text='Tags', icon='COLOR')
        row = box.row(align=True)
        row.prop_search(props, 'tags_input', props, 'tags_list', icon='VIEWZOOM')
        op = row.operator(f'object.{HANA3D_NAME}_add_tag', text='', icon='ADD')
        draw_selected_tags(box, props, f'object.{HANA3D_NAME}_remove_tag_upload')

        self._prop_needed(layout, props, 'publish_message', props.publish_message)

        if props.upload_state != '':
            label_multiline(layout, text=props.upload_state, width=context.region.width)
        if props.uploading:
            op = layout.operator(f'object.{HANA3D_NAME}_kill_bg_process', text='', icon='CANCEL')
            op.process_source = asset_type
            op.process_type = 'UPLOAD'
            box = box.column()
            box.enabled = False

        row = layout.row()
        row.scale_y = 2.0
        if props.view_id == '' or unified_props.workspace != props.view_workspace:
            optext = f'Upload {asset_type.lower()}'
            op = row.operator(f'object.{HANA3D_NAME}_upload', text=optext, icon='EXPORT')
            op.asset_type = asset_type

        if props.view_id != '' and unified_props.workspace == props.view_workspace:
            op = row.operator(
                f'object.{HANA3D_NAME}_upload',
                text='Upload as New Version',
                icon='RECOVER_LAST',
            )
            op.asset_type = asset_type
            op.reupload = True

            row = layout.row()
            op = row.operator(
                f'object.{HANA3D_NAME}_upload',
                text='Upload as New Asset',
                icon='PLUS',
            )
            op.asset_type = asset_type
            op.reupload = False

            layout.label(text='asset has a version online.')
