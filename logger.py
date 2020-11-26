import json
import pathlib
import os
import logging
from logging.handlers import RotatingFileHandler

import bpy

from .config import HANA3D_LOG_LEVEL, HANA3D_NAME
from .report_tools import execute_wrapper


def setup_logger():

    log_level = HANA3D_LOG_LEVEL

    logger = logging.getLogger('')
    logger.setLevel(logging.DEBUG)

    dir_path = os.path.join(os.getcwd(), 'logs')
    file_path = os.path.join(dir_path, 'hana3d.log')
    if not os.path.isdir(dir_path):
        os.mkdir(dir_path)

    file_handler = RotatingFileHandler(file_path, mode='a', maxBytes=5 * 1024 * 1024, backupCount=2)
    file_handler.setLevel(logging.DEBUG)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)

    blender_handler = BlenderHandler()
    blender_handler.setLevel(log_level)

    log_format = f'[%(asctime)s] {HANA3D_NAME} - %(name)s (%(filename)s:%(lineno)s) %(levelname)s: %(message)s'
    formatter = logging.Formatter(log_format)
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    blender_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    logger.addHandler(blender_handler)

    logger = logging.getLogger('urllib3')
    logger.setLevel(max(logging.root.level, logging.INFO))


class BlenderHandler(logging.StreamHandler):
    def emit(self, record):
        try:
            if hasattr(bpy.context.area, 'type'):
                text = record.msg
                type = record.levelname
                hana = getattr(bpy.ops, f'{HANA3D_NAME}')
                hana.info_report(text=f"{type}: {text}")
        except Exception:
            pass


class AppendInfo(bpy.types.Operator):
    """Append report on info tab"""

    bl_idname = f'{HANA3D_NAME}.info_report'
    bl_label = 'Append Report'
    bl_options = {'REGISTER'}

    type: bpy.props.StringProperty(
        name='type',
        default=''
    )
    text: bpy.props.StringProperty(
        name='text',
        default=''
    )

    @execute_wrapper
    def execute(self, context):
        # self.report({self.type}, self.text)
        return {'FINISHED'}


classes = (
    AppendInfo,
)


def register():
    for c in classes:
        bpy.utils.register_class(c)
