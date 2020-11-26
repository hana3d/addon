import json
import pathlib
import os
import logging
from logging.handlers import RotatingFileHandler

import bpy

from .config import HANA3D_LOG_LEVEL, HANA3D_NAME
from .report_tools import execute_wrapper
from .ui import AppendInfo


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
                hana.info(text=f"{type}: {text}")
        except Exception:
            pass


setup_logger()
