"""Blender application."""

import bpy


class Application(object):
    """Blender application."""

    def __init__(self):
        """Create an Application object."""

    def background(self):
        """Return True when blender is running without a user interface (started withk -b).

        Returns:
            bool: background
        """
        return bpy.app.background
