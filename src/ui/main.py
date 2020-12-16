"""Hana3D Blender UI class."""
import logging
from typing import List, Tuple

import bpy

from ..metaclasses.singleton import Singleton
from . import colors
from .report import Report
from .ui_types import Color


class UI(object, metaclass=Singleton):
    """Hana3D Blender UI singleton class."""

    def __init__(self) -> None:
        """Create a new UI instance."""
        self.active_window: bpy.types.Window = bpy.context.window
        self.active_area: bpy.type.Area = bpy.context.area
        self.active_region: bpy.types.Region = bpy.context.region
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

    def get_largest_view3d(self) -> Tuple[bpy.types.Window, bpy.types.Area, bpy.types.Region]:  # noqa: WPS210, E501
        """Get largest 3D View.

        Returns:
            bpy.types.Window: Window with the largest 3d view
            bpy.types.Area: Area with the largest 3d view
            bpy.types.Region: Region with the largest 3d view
        """
        maxsurf = 0
        maxa = None
        maxw = None
        maxr = None
        for window in bpy.context.window_manager.windows:
            for area in window.screen.areas:
                if area.type != 'VIEW_3D':
                    continue

                asurf = area.width * area.height
                if asurf <= maxsurf:
                    continue

                maxa = area
                maxw = window
                maxsurf = asurf

                for region in area.regions:
                    if region.type == 'WINDOW':
                        maxr = region  # noqa: WPS220

        self.active_window = maxw
        self.active_area = maxa
        self.active_region = maxr

        return maxw, maxa, maxr
