"""Blender UI Report class."""
import time

import bpy

from . import Color
from .bgl_helper import draw_text


class Report(object):
    """Blender UI Report."""

    def __init__(
        self,
        active_area: bpy.types.Area,
        text: str,
        timeout: float = 5,
        color: Color = (0.5, 1, 0.5, 1),
    ):
        """Create a Report object.

        Parameters:
            active_area: Area in which the report should be displayed
            text: Text to be displayed in the report
            timeout: How much time should the report be displayed on screen
            color: Color in which the report should be displayed
        """
        self._active_area = active_area
        self._text = text
        self._timeout = timeout
        self._start_time = time.time()
        self._color = color
        self._draw_color = color
        self._age = 0.0

    def fade(self) -> bool:
        """Fade a report object when it is close to its timeout.
        Return True if the report has timed out.
        """
        fade_time = 1
        self._age = time.time() - self._start_time
        if self._age + fade_time > self._timeout:
            alpha_multiplier = (self._timeout - self._age) / fade_time
            self._draw_color = (
                self._color[0],
                self._color[1],
                self._color[2],
                self._color[3] * alpha_multiplier,
            )
        return self._age > self._timeout

    def draw(self, x: float, y: float) -> None:
        if bpy.context.area == self._active_area:
            draw_text(self._text, x, y + 8, 16, self._draw_color)
