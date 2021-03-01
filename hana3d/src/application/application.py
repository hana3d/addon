"""Blender application."""

import bpy


class Application(object):
    """Blender application."""

    def __init__(self) -> None:
        """Create an Application object."""

    def background(self) -> bool:
        """Return True when blender is running without a user interface (started with -b).

        Returns:
            bool: background
        """
        return bpy.app.background
