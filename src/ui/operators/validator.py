"""Shows validation panel before upload"""
import logging
from typing import Tuple

import bpy
from bpy.props import IntProperty

from ...validators import BaseValidator
from ...validators.uv_check import uv_checker
from ....config import (
    HANA3D_DESCRIPTION,
    HANA3D_MODELS,
    HANA3D_NAME,
    HANA3D_UI,
)
from ....report_tools import execute_wrapper

validators : Tuple[BaseValidator] = (
    uv_checker,
)

class IgnoreOperator(bpy.types.Operator):  # noqa: WPS338, WPS214
    """Ignore warnings"""

    bl_idname = f'message.{HANA3D_NAME}_validation_ignore'
    bl_label = f'{HANA3D_DESCRIPTION} Validation Ignore'
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    index = IntProperty(
        name="Index",
        description="Index"
    )

    def execute(self, context):  # noqa: D102
        validator = validators[self.index]
        logging.info(f'Ignoring validator {validator.name}')
        validator.ignore()
        return {'FINISHED'}


class FixOperator(bpy.types.Operator):  # noqa: WPS338, WPS214
    """Fix validation problems"""

    bl_idname = f'message.{HANA3D_NAME}_validation_fix'
    bl_label = f'{HANA3D_DESCRIPTION} Validation Fix'
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    index = IntProperty(
        name="Index",
        description="Index"
    )

    def execute(self, context):  # noqa: D102
        validator = validators[self.index]
        logging.info(f'Fixing validator {validator.name}')
        validator.run_fix()
        return {'FINISHED'}


class ValidationPanel(bpy.types.Operator):  # noqa: WPS338, WPS214
    """Shows validation panel before upload"""

    bl_idname = f'message.{HANA3D_NAME}_validation_panel'
    bl_label = f'{HANA3D_DESCRIPTION} Validation Panel UI'
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    @execute_wrapper
    def execute(self, context):  # noqa: D102
        logging.info('Executing validator')
        return {'FINISHED'}
 
    def invoke(self, context, event):
        logging.info('Invoking validator')
        for validator in validators:
            validator.run_validation()
        return context.window_manager.invoke_props_dialog(self, width = 900)

    def draw(self, context):
        for i, validator in enumerate(validators):
            box = self.layout.box()
            box.label(text=validator.name)
            info = box.row()
            info.label(text=validator.category)
            info.label(text=validator.description)
            fix = info.operator(f'message.{HANA3D_NAME}_validation_fix', text='Fix', icon='SETTINGS')
            fix.index = i
            ignore = info.operator(f'message.{HANA3D_NAME}_validation_ignore', text='Ignore', icon='CANCEL')
            ignore.index = i
            result = box.row()
            valid, message = validator.get_validation_result()
            icon = 'CHECKMARK' if valid else 'CANCEL'
            result.alert = not valid
            result.label(text=message, icon=icon)
