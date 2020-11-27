"""User preferences."""

from dataclasses import dataclass

import bpy

from ...config import HANA3D_NAME


class Preferences(object):
    """Hana3D addon preferences."""

    def __init__(self):
        """Create a Preferences object."""

    def get(self):
        """Get User Preferences object.

        Returns:
            UserPreferences: user_preferences
        """
        return bpy.context.preferences.addons[HANA3D_NAME].preferences  # noqa: WPS219, E501


# TODO: use this dataclass
@dataclass
class UserPreferences(object):
    """Hana3D User Preferences."""

    api_key: str
    api_key_timeout: int
    api_key_life: str
    id_token: str
