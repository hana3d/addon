"""Shows validation panel before upload."""
import logging
from typing import Tuple

import bpy
from bpy.props import IntProperty

from ...validators import BaseValidator
from ...validators.uv_check import uv_checker
from ....config import HANA3D_DESCRIPTION, HANA3D_NAME
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
        for validator in validators:
            validator.run_validation()
        return context.window_manager.invoke_props_dialog(self, width=900)  # noqa: WPS432

    def draw(self, context):  # noqa: D102
        for index, validator in enumerate(validators):
            box = self.layout.box()
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
            report = box.row()
            valid, message = validator.get_validation_result()
            icon = 'CHECKMARK' if valid else 'CANCEL'
            report.alert = not valid
            report.label(text=message, icon=icon)
