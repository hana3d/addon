import json
import pathlib
import os
import logging
from logging.handlers import RotatingFileHandler
from typing import Tuple

import bpy

from . import colors, ui
from .config import HANA3D_LOG_LEVEL, HANA3D_NAME
from .report_tools import execute_wrapper


def setup_logger():

    log_level = HANA3D_LOG_LEVEL
    logger = logging.getLogger(HANA3D_NAME)
    logger.setLevel(logging.DEBUG)

    dir_path = os.path.join(os.getcwd(), 'hana3d_logs')
    log_file_path = os.path.join(dir_path, 'hana3d_logs.log')
    report_file_path = os.path.join(dir_path, 'hana3d_report.log')
    if not os.path.isdir(dir_path):
        os.mkdir(dir_path)

    report_file_handler = logging.FileHandler(report_file_path, mode='w')
    report_file_handler.setLevel(logging.DEBUG)

    log_file_handler = RotatingFileHandler(
        log_file_path,
        mode='a',
        maxBytes=5 * 1024 * 1024,
        backupCount=2
    )
    log_file_handler.setLevel(logging.DEBUG)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)

    blender_handler = BlenderHandler()
    blender_handler.setLevel(log_level)

    log_format = f'[%(asctime)s] {HANA3D_NAME} - %(name)s (%(filename)s:%(lineno)s) %(levelname)s: %(message)s'
    formatter = logging.Formatter(log_format)
    log_file_handler.setFormatter(formatter)
    report_file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    blender_handler.setFormatter(formatter)

    logger.addHandler(log_file_handler)
    logger.addHandler(report_file_handler)
    logger.addHandler(console_handler)
    logger.addHandler(blender_handler)

    url_logger = logging.getLogger('urllib3')
    url_logger.setLevel(max(logger.level, logging.INFO))


class BlenderHandler(logging.StreamHandler):
    def emit(self, record):
        try:
            if hasattr(bpy.context.area, 'type'):
                text = record.msg
                type = record.levelname
                hana = getattr(bpy.ops, f'{HANA3D_NAME}')
                hana.log_info(text=f"{type}: {text}")
        except Exception:
            pass


class AppendInfo(bpy.types.Operator):
    """Append report on info tab"""

    bl_idname = f'{HANA3D_NAME}.log_info'
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


def show_report(
        props=None,
        text: str = '',
        timeout: int = 5,
        color: Tuple = colors.GREEN):
    ui.add_report(text=text, timeout=timeout, color=color)
    hana_type = str(type(props))
    if "SearchProps" in hana_type:
        props.report = text
    elif "UploadProps" in hana_type:
        props.upload_state = text


classes = (
    AppendInfo,
)


def register():
    for c in classes:
        bpy.utils.register_class(c)
