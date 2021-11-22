"""Shows validation panel before upload."""
import logging
from typing import List

import bpy
from bpy.props import IntProperty

from ...unified_props import Unified
from ...upload.upload import get_upload_props
from ...validators import BaseValidator, Category, dummy_fix_function
from ...validators.animated_meshes_check import animated_meshes_check
from ...validators.animation_count import animation_count
from ...validators.joint_count import joint_count
from ...validators.missing_references import missing_references_check
from ...validators.morph_target_check import morph_target_checker
from ...validators.object_count import object_count
from ...validators.scale_check import scale_check
from ...validators.square_textures import square_textures
from ...validators.textures_size import textures_size
from ...validators.uv_check import uv_checker
from ...validators.vertex_color_check import vertex_color_checker
from ....config import HANA3D_DESCRIPTION, HANA3D_NAME, HANA3D_UI
from ....report_tools import execute_wrapper

validators: List[BaseValidator] = [
    animated_meshes_check,
    animation_count,
    # double_sided,
    joint_count,
    # material_count,
    missing_references_check,
    morph_target_checker,
    object_count,
    scale_check,
    square_textures,
    textures_size,
    # triangle_count,
    uv_checker,
    vertex_color_checker,
]


class IgnoreOperator(bpy.types.Operator):
    """Ignore warnings."""

    bl_idname = f'message.{HANA3D_NAME}_validation_ignore'
    bl_label = f'{HANA3D_DESCRIPTION} Validation Ignore'
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    index: IntProperty(  # type: ignore
        name='Index',
        description='Index',
        default=-1,
        options={'SKIP_SAVE'},
    )

    def execute(self, context):  # noqa: D102
        if self.index > -1:
            validator = validators[self.index]
            logging.info(f'Ignoring validator {validator.name}')
            validator.ignore()
        else:
            logging.info('Ignoring all validators')
            for validator in validators:  # noqa: WPS440
                validator.ignore()
        return {'FINISHED'}


class FixOperator(bpy.types.Operator):  # noqa: WPS338, WPS214
    """Fix validation problems."""

    bl_idname = f'message.{HANA3D_NAME}_validation_fix'
    bl_label = f'{HANA3D_DESCRIPTION} Validation Fix'
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    index: IntProperty(  # type: ignore
        name='Index',
        description='Index',
        default=-1,
        options={'SKIP_SAVE'},
    )

    def execute(self, context):  # noqa: D102
        if self.index > -1:
            validator = validators[self.index]
            validator.run_fix()
            logging.info(f'Fixing validator {validator.name}')
        else:
            logging.info('Fixing all validators')
            for validator in validators:  # noqa: WPS440
                validator.run_fix()
        return {'FINISHED'}


class ValidationPanel(bpy.types.Operator):  # noqa: WPS338, WPS214
    """Shows validation panel before upload."""

    bl_idname = f'message.{HANA3D_NAME}_validation_panel'
    bl_label = f'{HANA3D_DESCRIPTION} Validation Panel UI'
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    @execute_wrapper
    def execute(self, context):  # noqa: D102
        logging.info('Executing validator')
        return {'FINISHED'}

    def invoke(self, context, event):  # noqa: D102
        logging.info('Invoking validator')
        upload_props = get_upload_props()
        upload_props.skip_post_process = False
        for validator in validators:
            validator.run_validation()
            valid, _ = validator.get_validation_result()
            if not valid and validator.category == Category.error:
                upload_props.skip_post_process = True
        return context.window_manager.invoke_props_dialog(self, width=900)  # noqa: WPS432

    def _get_asset_type_from_ui(self):
        uiprops = getattr(bpy.context.window_manager, HANA3D_UI)
        return uiprops.asset_type_upload

    def draw(self, context):  # noqa: D102
        error_dict = {
            Category.warning: 0,
            Category.error: 0,
        }

        row = self.layout.row()
        row.operator(
            f'message.{HANA3D_NAME}_validation_fix',
            text='Fix all',
            icon='SETTINGS',
        )
        row.operator(
            f'message.{HANA3D_NAME}_validation_ignore',
            text='Ignore all',
            icon='CANCEL',
        )

        for index, validator in enumerate(validators):
            valid, message = validator.get_validation_result()
            if not valid:
                box = self.layout.box()
                self._draw_overview(box, index, validator)
                self._draw_report(box, valid, message)
                error_dict[validator.category] += 1

        if error_dict[Category.error] > 0:
            self.layout.label(
                text=f'{error_dict[Category.error]} errors detected, conversions will not run.',
            )
        if error_dict[Category.warning] > 0:
            self.layout.label(
                text=f'{error_dict[Category.warning]} warnings detected.',
            )
        self._draw_upload_buttons(context)

    def _draw_overview(self, box, index: int, validator: BaseValidator):
        box.label(text=validator.name)
        overview = box.row()
        overview.label(text=validator.category)
        overview.label(text=validator.description)
        fix_column = overview.column()
        fix = fix_column.operator(
            f'message.{HANA3D_NAME}_validation_fix',
            text='Fix',
            icon='SETTINGS',
        )
        fix.index = index
        fix_column.enabled = validator.fix_function != dummy_fix_function

        ignore_column = overview.column()
        ignore = ignore_column.operator(
            f'message.{HANA3D_NAME}_validation_ignore',
            text='Ignore',
            icon='CANCEL',
        )
        ignore.index = index

    def _draw_report(self, box, valid: bool, message: str):
        report = box.row()
        icon = 'CHECKMARK' if valid else 'CANCEL'
        report.alert = not valid
        report.label(text=message, icon=icon)

    def _draw_upload_buttons(self, context):
        asset_type = self._get_asset_type_from_ui()
        unified_props = Unified(context).props
        upload_props = get_upload_props()
        row = self.layout.row()
        row.scale_y = 2.0

        if upload_props.view_id == '' or unified_props.workspace != upload_props.view_workspace:
            optext = f'Upload {asset_type.lower()}'
            op = row.operator(f'object.{HANA3D_NAME}_upload', text=optext, icon='EXPORT')
            op.asset_type = asset_type

        if upload_props.view_id != '' and unified_props.workspace == upload_props.view_workspace:
            op = row.operator(
                f'object.{HANA3D_NAME}_upload',
                text='Reupload',
                icon='RECOVER_LAST',
            )
            op.asset_type = asset_type
            op.reupload = True

            op = row.operator(
                f'object.{HANA3D_NAME}_upload',
                text='Upload as New Asset',
                icon='PLUS',
            )
            op.asset_type = asset_type
            op.reupload = False
