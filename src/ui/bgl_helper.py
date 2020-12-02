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
from typing import List, Optional, Tuple

import bgl
import blf
import bpy
import gpu
from gpu_extras.batch import batch_for_shader
from mathutils import Euler, Vector

from .ui_types import BlenderSequence, Color


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
    crop: Color = (0, 0, 1, 1),
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


def draw_bbox(  # noqa: WPS210, WPS211
    location: BlenderSequence,
    rotation: BlenderSequence,
    bbox_min: BlenderSequence,
    bbox_max: BlenderSequence,
    progress: Optional[float] = None,
    color: Color = (0, 1, 0, 1),
) -> None:
    """Draw a bounding box on the screen.

    Parameters:
        location: Location to which the bounding box should be translated
        rotation: Rotation that should be applied to the bounding box
        bbox_min: Minimun coordinates of the bounding box
        bbox_max: Maximum coordinates of the bounding box
        progress: Progress to be drawn on the bounding box
        color: Color in which the bounding box should be drawn
    """
    rotation = Euler(rotation)

    smin = Vector(bbox_min)
    smax = Vector(bbox_max)
    v0 = Vector(smin)
    v1 = Vector((smax.x, smin.y, smin.z))
    v2 = Vector((smax.x, smax.y, smin.z))
    v3 = Vector((smin.x, smax.y, smin.z))
    v4 = Vector((smin.x, smin.y, smax.z))
    v5 = Vector((smax.x, smin.y, smax.z))
    v6 = Vector((smax.x, smax.y, smax.z))
    v7 = Vector((smin.x, smax.y, smax.z))

    arrowx = smin.x + (smax.x - smin.x) / 2
    arrowy = smin.y - (smax.x - smin.x) / 2
    v8 = Vector((arrowx, arrowy, smin.z))

    vertices = [v0, v1, v2, v3, v4, v5, v6, v7, v8]
    for vertice in vertices:
        vertice.rotate(rotation)
        vertice += Vector(location)

    lines = [
        [0, 1],
        [1, 2],
        [2, 3],
        [3, 0],
        [4, 5],
        [5, 6],
        [6, 7],
        [7, 4],
        [0, 4],
        [1, 5],
        [2, 6],
        [3, 7],
        [0, 8],
        [1, 8],
    ]

    draw_lines(vertices, lines, color)
    if progress is not None:
        color = (color[0], color[1], color[2], 0.2)
        progress = progress * 0.01  # noqa: WPS432
        vz0 = (v4 - v0) * progress + v0
        vz1 = (v5 - v1) * progress + v1
        vz2 = (v6 - v2) * progress + v2
        vz3 = (v7 - v3) * progress + v3
        rects = (
            (v0, v1, vz1, vz0),
            (v1, v2, vz2, vz1),
            (v2, v3, vz3, vz2),
            (v3, v0, vz0, vz3),
        )
        for rect in rects:
            draw_rect3d(rect, color)
