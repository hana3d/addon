"""Hana3D Blender UI class."""
import logging
from typing import List

import bpy

from ..metaclasses.singleton import Singleton
from . import colors
from .report import Report
from .ui_types import Color


class UI(object, metaclass=Singleton):
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
