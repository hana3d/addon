import time

import bpy

from ...ui_bgl import draw_text


class Report:
    def __init__(self, active_area: bpy.types.Area, text='', timeout=5, color=(0.5, 1, 0.5, 1)):
        self.active_area = active_area
        self.text = text
        self.timeout = timeout
        self.start_time = time.time()
        self.color = color
        self.draw_color = color
        self.age = 0.0

    def fade(self) -> bool:
        fade_time = 1
        self.age = time.time() - self.start_time
        if self.age + fade_time > self.timeout:
            alpha_multiplier = (self.timeout - self.age) / fade_time
            self.draw_color = (
                self.color[0],
                self.color[1],
                self.color[2],
                self.color[3] * alpha_multiplier,
            )
        return self.age > self.timeout

    def draw(self, x: float, y: float) -> None:
        if bpy.context.area == self.active_area:
            draw_text(self.text, x, y + 8, 16, self.draw_color)
