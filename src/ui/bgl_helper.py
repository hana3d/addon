# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####
"""Module containing helper methods for drawing using bgl."""
from typing import List, Tuple

import bgl
import blf
import bpy
import gpu
from gpu_extras.batch import batch_for_shader
from mathutils import Vector

from .ui_types import Color


def draw_rect(
    x: float,  # noqa: WPS111
    y: float,  # noqa: WPS111
    width: float,
    height: float,
    color: Color,
) -> None:
    """Draw a rectangle in the xy-plane.

    Parameters:
        x: Bottom-left x-coordinate
        y: Bottom-left y-coordinate
        width: Width of the rectangle
        height: Height of the rectangle
        color: Color in which the rectangle should be drawn
    """
    points = [
        [x, y],
        [x, y + height],
        [x + width, y + height],
        [x + width, y],
    ]
    indices = ((0, 1, 2), (2, 3, 0))

    shader = gpu.shader.from_builtin('2D_UNIFORM_COLOR')
    batch = batch_for_shader(shader, 'TRIS', {'pos': points}, indices=indices)

    shader.bind()
    shader.uniform_float('color', color)
    bgl.glEnable(bgl.GL_BLEND)
    batch.draw(shader)


def draw_line2d(x1: float, y1: float, x2: float, y2: float, color: Color) -> None:
    """Draw a line.

    Parameters:
        x1: First point x-coordinate
        y1: First point y-coordinate
        x2: Second point x-coordinate
        y2: Second point y-coordinate
        color: Color in which the line should be drawn
    """
    coords = ((x1, y1), (x2, y2))

    indices = ((0, 1),)
    bgl.glEnable(bgl.GL_BLEND)

    shader = gpu.shader.from_builtin('2D_UNIFORM_COLOR')
    batch = batch_for_shader(shader, 'LINES', {'pos': coords}, indices=indices)
    shader.bind()
    shader.uniform_float('color', color)
    batch.draw(shader)


def draw_lines(vertices: List[Vector], indices: List[List[int]], color: Color) -> None:
    """Draw a set of lines.

    Parameters:
        vertices: Coordinate of each of the points
        indices: List containing pairs of how the points should connect
        color: Color in which the lines should be drawn
    """
    bgl.glEnable(bgl.GL_BLEND)

    shader = gpu.shader.from_builtin('3D_UNIFORM_COLOR')
    batch = batch_for_shader(shader, 'LINES', {'pos': vertices}, indices=indices)
    shader.bind()
    shader.uniform_float('color', color)
    batch.draw(shader)


def draw_rect3d(coords: Tuple[Vector, Vector, Vector, Vector], color: Color) -> None:
    """Draw a rectangle without plane restriction.

    Parameters:
        coords: Coordinates of the rectangle to be drawn
        color: Color in which the rectangle should be drawn
    """
    indices = [(0, 1, 2), (2, 3, 0)]
    shader = gpu.shader.from_builtin('3D_UNIFORM_COLOR')
    batch = batch_for_shader(shader, 'TRIS', {'pos': coords}, indices=indices)
    shader.uniform_float('color', color)
    batch.draw(shader)


def draw_image(  # noqa: WPS210, WPS211
    x: float,  # noqa: WPS111
    y: float,  # noqa: WPS111
    width: float,
    height: float,
    image: bpy.types.Image,
    transparency: float,
    crop=(0, 0, 1, 1),
) -> None:
    """Draw a image on the screen.

    Parameters:
        x: Bottom-left x-coordinate
        y: Bottom-left y-coordinate
        width: Width of the image
        height: Height of the image
        image: Image to be drawn
        transparency: Image transparency
        crop: Tuple describing how the image should be cropped

    Raises:
        Exception: Failed to load into an OpenGL texture
    """
    coords = [
        (x, y),
        (x + width, y),
        (x, y + height),
        (x + width, y + height),
    ]

    uvs = [
        (crop[0], crop[1]),
        (crop[2], crop[1]),
        (crop[0], crop[3]),
        (crop[2], crop[3]),
    ]

    indices = [(0, 1, 2), (2, 1, 3)]

    shader = gpu.shader.from_builtin('2D_IMAGE')
    batch = batch_for_shader(shader, 'TRIS', {'pos': coords, 'texCoord': uvs}, indices=indices)

    # send image to gpu if it isn't there already
    if image.gl_load():
        raise Exception()

    # texture identifier on gpu
    texture_id = image.bindcode

    # in case someone disabled it before
    bgl.glEnable(bgl.GL_BLEND)

    # bind texture to image unit 0
    bgl.glActiveTexture(bgl.GL_TEXTURE0)
    bgl.glBindTexture(bgl.GL_TEXTURE_2D, texture_id)

    shader.bind()
    # tell shader to use the image that is bound to image unit 0
    shader.uniform_int('image', 0)
    batch.draw(shader)

    bgl.glDisable(bgl.GL_TEXTURE_2D)


def draw_text(
    text: str,
    x: float,  # noqa: WPS111
    y: float,  # noqa: WPS111
    size: float,
    color: Color = (1, 1, 1, 0.5),
) -> None:
    """Draw text on the screen.

    Parameters:
        text: text to be drawn
        x: x-coordinate of where the text should be drawn
        y: y-coordinate of where the text should be drawn
        size: Point size of the font
        color: Color in which the text should be drawn
    """
    font_id = 0
    blf.color(font_id, color[0], color[1], color[2], color[3])  # noqa: WPS221
    blf.position(font_id, x, y, 0)
    dpi = 72
    blf.size(font_id, size, dpi)
    blf.draw(font_id, text)
