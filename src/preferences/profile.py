"""Hana3D Profile."""

import bpy

from ...config import HANA3D_PROFILE


class Profile(object):
    """Hana3D user profile."""

    def __init__(self):
        """Create a Profile object."""

    def user_profile(self):
        """Get User Profile object.

        Returns:
            dict: user_profile
        """
        return bpy.context.window_manager.get(HANA3D_PROFILE)
