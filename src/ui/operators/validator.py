"""Shows validation panel before upload."""
import logging
from typing import Tuple

import bpy
from bpy.props import IntProperty

from ...validators import BaseValidator
from ...validators.uv_check import uv_checker
from ....config import HANA3D_DESCRIPTION, HANA3D_NAME, HANA3D_UI
from ....report_tools import execute_wrapper

validators: Tuple[BaseValidator] = (
    uv_checker,
)


class IgnoreOperator(bpy.types.Operator):
    """Ignore warnings."""

    bl_idname = f'message.{HANA3D_NAME}_validation_ignore'
    bl_label = f'{HANA3D_DESCRIPTION} Validation Ignore'
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    index = IntProperty(
        name='Index',
        description='Index',
    )

    def execute(self, context):  # noqa: D102
        validator = validators[self.index]
        logging.info(f'Ignoring validator {validator.name}')
        validator.ignore()
        return {'FINISHED'}


class FixOperator(bpy.types.Operator):  # noqa: WPS338, WPS214
    """Fix validation problems."""

    bl_idname = f'message.{HANA3D_NAME}_validation_fix'
    bl_label = f'{HANA3D_DESCRIPTION} Validation Fix'
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    index = IntProperty(
        name='Index',
        description='Index',
    )

    errors = IntProperty(
        name='Errors',
        description='Error count',
        default=0,
    )

    warnings = IntProperty(
        name='Warnings',
        description='Warning count',
        default=0,
    )

    def execute(self, context):  # noqa: D102
        validator = validators[self.index]
        logging.info(f'Fixing validator {validator.name}')
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
        self.errors = 0
        self.warnings = 0
        for validator in validators:
            validator.run_validation()
            valid, _ = validator.get_validation_result()
            if not valid:
                if validator.category == 'WARNING':
                    self.warnings += 1
                elif validator.category == 'ERROR':
                    self.errors += 1
        return context.window_manager.invoke_props_dialog(self, width=900)  # noqa: WPS432

    def _get_asset_type_from_ui(self):
        uiprops = getattr(bpy.context.window_manager, HANA3D_UI)
        return uiprops.asset_type_upload.lower()

    def draw(self, context):  # noqa: D102
        for index, validator in enumerate(validators):
            box = self.layout.box()
            self._draw_overview(box, index, validator)
            valid, message = validator.get_validation_result()
            self._draw_report(box, valid, message)
        if self.errors > 0:
            self.layout.label(text=f'{self.errors} errors detected, cannot upload.')
            return
        elif self.warnings > 0:
            self.layout.label(text=f'{self.warnings} warnings detected, conversions will not run.')
        self._draw_upload_buttons()

    def _draw_overview(self, box, index: int, validator: BaseValidator):
        box.label(text=validator.name)
        overview = box.row()
        overview.label(text=validator.category)
        overview.label(text=validator.description)
        fix = overview.operator(
            f'message.{HANA3D_NAME}_validation_fix',
            text='Fix',
            icon='SETTINGS',
        )
        fix.index = index
        ignore = overview.operator(
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

    def _draw_upload_buttons(self):
        asset_type = self._get_asset_type_from_ui()
        row = self.layout.row()
        op = row.operator(
            f'object.{HANA3D_NAME}_upload',
            text='Upload as New Version',
            icon='RECOVER_LAST',
        )
        op.asset_type = asset_type
        op.reupload = True

        row = self.layout.row()
        op = row.operator(
            f'object.{HANA3D_NAME}_upload',
            text='Upload as New Asset',
            icon='PLUS',
        )
        op.asset_type = asset_type
        op.reupload = False
