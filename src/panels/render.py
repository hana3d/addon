"""Render Farm operations panel."""
from bpy.types import Panel

from ..upload import upload
from ...config import HANA3D_DESCRIPTION, HANA3D_NAME, HANA3D_RENDER, HANA3D_UI


class Hana3DRenderPanel(Panel):  # noqa: WPS214
    """Render Farm operations panel."""

    bl_label = f'Manage renders on {HANA3D_DESCRIPTION}'
    bl_idname = f'VIEW3D_PT_{HANA3D_NAME}_RenderPanel'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = HANA3D_DESCRIPTION
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):  # noqa: D102
        return True

    def draw(self, context):  # noqa: D102,WPS213
        render_props = getattr(context.window_manager, HANA3D_RENDER)
        asset_props = upload.get_upload_props()
        ui_props = getattr(context.window_manager, HANA3D_UI)

        self.layout.prop(ui_props, 'asset_type_render', expand=False, text='')

        if asset_props is None:
            row = self.layout.row()
            row.label(text='Select an asset')
            return

        self._draw_asset_name(ui_props, render_props)
        self.layout.separator()

        if asset_props.view_id == '':
            row = self.layout.row()
            row.label(text='Upload asset first')
            return

        self._draw_main_panel(render_props, asset_props)
        self.layout.separator()

        self.layout.prop(render_props, 'render_ui_mode', expand=True, icon_only=False)
        self.layout.separator()

        if render_props.render_ui_mode == 'GENERATE':
            self._draw_generate_panel(context, render_props, asset_props)
        elif render_props.render_ui_mode == 'UPLOAD':
            self._draw_upload_panel(asset_props)

    def _draw_asset_name(self, ui_props, render_props):
        if ui_props.asset_type_upload == 'MODEL':
            icon = 'OBJECT_DATAMODE'
        elif ui_props.asset_type_upload == 'SCENE':
            icon = 'SCENE_DATA'
        elif ui_props.asset_type_upload == 'MATERIAL':
            icon = 'MATERIAL'
        row = self.layout.row()
        row.prop(render_props, 'asset', text='Asset', icon=icon)

    def _draw_main_panel(self, render_props, asset_props):
        if 'jobs' not in asset_props.render_data or not asset_props.render_data['jobs']:
            row = self.layout.row()
            row.label(text=f'This asset has no saved renders in {HANA3D_DESCRIPTION}')
            return

        box = self.layout.box()
        row = box.row()
        row.template_list(
            listtype_name='RENDER_UL_List',
            list_id='render_list',
            dataptr=asset_props,
            propname='render_list',
            active_dataptr=asset_props,
            active_propname='render_list_index',
            item_dyntip_propname='not_working',
        )
        row = box.row()
        row.template_icon(
            icon_value=asset_props.render_list[asset_props.render_list_index]['icon_id'],
            scale=10,
        )

    def _draw_generate_panel(self, context, render_props, asset_props):  # noqa: WPS213
        box = self.layout.box()

        row = box.row()
        row.label(text='Balance')
        row.label(text=render_props.balance)

        box.label(text='Render Parameters', icon='PREFERENCES')
        box.prop(asset_props, 'render_job_name', text='Name')
        box.prop(render_props, 'cameras', expand=False, icon_only=False)
        if render_props.cameras == 'ACTIVE_CAMERA' and context.scene.camera is not None:
            row = box.row()
            row.label(text=context.scene.camera.name_full)
        box.prop(render_props, 'engine')
        row = box.row()
        row.label(text='Resolution X')
        row.prop(context.scene.render, 'resolution_x', text='')
        row = box.row()
        row.label(text='Resolution Y')
        row.prop(context.scene.render, 'resolution_y', text='')

        row = box.row()
        row.prop(render_props, 'frame_animation', text='')
        if render_props.cameras in {'VISIBLE_CAMERAS', 'ALL_CAMERAS'}:
            row.enabled = False
            row = box.row()
            row.label(text='Frame')
            row.prop(context.scene, 'frame_current', text='')
            row = box.row()
            row.label(text='Atenção! Só será renderizado um frame por câmera!', icon='ERROR')
        elif render_props.frame_animation == 'FRAME':
            row = box.row()
            row.label(text='Frame')
            row.prop(context.scene, 'frame_current', text='')
        elif render_props.frame_animation == 'ANIMATION':
            row = box.row()
            row.label(text='Frame Start')
            row.prop(context.scene, 'frame_start', text='')
            row = box.row()
            row.label(text='Frame End')
            row.prop(context.scene, 'frame_end', text='')

        if asset_props is not None and asset_props.rendering:
            self._draw_kill_job(asset_props)

        self._draw_render_button(context, render_props)

    def _draw_render_button(self, context, render_props):
        cameras = [ob for ob in context.scene.objects if ob.type == 'CAMERA']

        active_camera = render_props.cameras == 'ACTIVE_CAMERA' and context.scene.camera is not None
        visible_cameras = (
            render_props.cameras == 'VISIBLE_CAMERAS' and any(ob.visible_get() for ob in cameras)
        )
        all_cameras = render_props.cameras == 'ALL_CAMERAS' and len(cameras)

        if active_camera or visible_cameras or all_cameras:
            row = self.layout.row()
            row.scale_y = 2.0
            row.operator(f'{HANA3D_NAME}.render_scene', icon='SCENE')

    def _draw_kill_job(self, asset_props):
        row = self.layout.row(align=True)
        row.label(text=asset_props.render_state)
        op = row.operator(f'{HANA3D_NAME}.cancel_render_job', text='', icon='CANCEL')
        op.view_id = asset_props.view_id

    def _draw_upload_panel(self, asset_props):
        box = self.layout.box()

        row = box.row()
        row.prop(asset_props, 'active_image', text='')
        row.operator(f'{HANA3D_NAME}.open_image', text='', icon='FILEBROWSER')

        row = box.row()
        row.prop(asset_props, 'render_job_name', text='Name')
        row = box.row()
        row.label(text=asset_props.upload_render_state)
        row = box.row()
        row.operator(f'{HANA3D_NAME}.upload_render_image', icon='EXPORT')
