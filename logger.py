"""Logging configs."""

import logging
import os
import re
from logging.handlers import RotatingFileHandler
from os.path import expanduser
from typing import Tuple

import bpy

from . import colors, ui
from .config import HANA3D_LOG_LEVEL, HANA3D_NAME
from .report_tools import execute_wrapper


def setup_logger(): # noqa WPS210,WPS213
    """Logger setup."""
    log_level = HANA3D_LOG_LEVEL
    logger = logging.getLogger('')
    logger.setLevel(logging.DEBUG)

    dir_path = os.path.join(expanduser('~'), 'hana3d_logs')
    log_file_path = os.path.join(dir_path, f'{HANA3D_NAME}_logs.log')
    report_file_path = os.path.join(dir_path, f'{HANA3D_NAME}_report.log')
    if not os.path.isdir(dir_path):
        os.mkdir(dir_path)

    report_file_handler = logging.FileHandler(report_file_path, mode='w')
    report_file_handler.setLevel(logging.DEBUG)

    log_file_handler = RotatingFileHandler(
        log_file_path,
        mode='a',
        maxBytes=5 * 1024 * 1024,
        backupCount=2,
    )
    log_file_handler.setLevel(logging.DEBUG)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)

    blender_handler = BlenderHandler()
    blender_handler.setLevel(log_level)

    log_format = '[%(asctime)s] %(name)s (%(filename)s:%(lineno)s) %(levelname)s: %(message)s' # noqa WPS323
    formatter = logging.Formatter(log_format)
    log_file_handler.setFormatter(formatter)
    report_file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    blender_handler.setFormatter(formatter)

    logger.addHandler(log_file_handler)
    logger.addHandler(report_file_handler)

    if len(logger.handlers) < 3:
        logger.addHandler(console_handler)
        logger.addHandler(blender_handler)

    url_logger = logging.getLogger('urllib3')
    url_logger.setLevel(max(logger.level, logging.INFO))


class BlenderHandler(logging.StreamHandler):
    """Logging handler that shows logs on Blender Info Tab."""

    def emit(self, record):
        """
        Emit.

        Parameters:
            record: automatically added from logging
        """
        try:
            if bpy.context.area.type:
                text = record.msg
                level = record.levelname
                stage = re.match(r'.*(hana3d_.*)\\.*', record.pathname)
                hana = getattr(bpy.ops, stage.groups(0)[0])
                hana.log_info(text=f'{level}: {text}')
        except Exception: # noqa S110
            pass # noqa WPS420


class AppendInfo(bpy.types.Operator):
    """Append report on info tab."""

    bl_idname = f'{HANA3D_NAME}.log_info'
    bl_label = 'Append Report'
    bl_options = {'REGISTER'}

    level: bpy.props.StringProperty(
        name='type',
        default='',
    )
    text: bpy.props.StringProperty(
        name='text',
        default='',
    )

    @execute_wrapper
    def execute(self, context):
        """
        Execute.

        Parameters:
            context: blender context

        Returns:
            state: blender state
        """
        # noqa E800 self.report({self.level}, self.text)
        pass # noqa S110 
        return {'FINISHED'}


def show_report(
    props=None,
    text: str = '',
    timeout: int = 5,
    color: Tuple = colors.GREEN,
):
    """
    Show report on UI and Addon.

    Parameters:
        props: props related to the right part of the addon
        text: text of the report
        timeout: seconds it will be displayed on UI
        color: color that will be displayed on UI
    """
    ui.add_report(text=text, timeout=timeout, color=color)
    hana_type = str(type(props))
    if 'SearchProps' in hana_type:
        props.report = text
    elif 'UploadProps' in hana_type:
        props.upload_state = text


classes = (
    AppendInfo,
)


def register():
    """Register."""
    for cl in classes:
        bpy.utils.register_class(cl)


def unregister():
    """Unregister."""
    for cl in classes:
        bpy.utils.unregister_class(cl)
