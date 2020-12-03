"""Hana3D Blender UI class."""

import logging
from typing import Dict, List, Type

import bpy

from . import colors
from .report import Report
from .ui_types import Color


# See https://stackoverflow.com/questions/6760685/creating-a-singleton-in-python
# for more context in how to implement a singleton in Python
class _Singleton(type):
    # See https://www.python.org/dev/peps/pep-0484/#the-problem-of-forward-declarations
    _instances: Dict[Type['_Singleton'], Type['UI']] = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]


class UI(object, metaclass=_Singleton):
    """Hana3D Blender UI singleton class."""

    def __init__(self) -> None:
        """Create a new UI instance."""
        self.active_area: bpy.type.Area = bpy.context.area
        self.reports: List[Report] = []

    def add_report(self, text: str = '', timeout: int = 5, color: Color = colors.GREEN) -> None:
        """Create a new UI user report.

        Parameters:
            text: Text that will be displayed to the user
            timeout: Time in seconds during which the text will be displayed
            color: Color in which the text should be displayed
        """
        # check for same reports and just make them longer by the timeout.
        for old_report in self.reports:
            if old_report.check_refresh(text, timeout):
                return
        logging.info(f'Message showed to the user: {text}')
        report = Report(self.active_area, text, timeout=timeout, color=color)
        self.reports.append(report)
