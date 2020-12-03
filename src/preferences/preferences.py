"""User preferences."""

from dataclasses import dataclass

import bpy

from ...config import HANA3D_NAME


@dataclass
class UserPreferences(object):
    """Hana3D User Preferences."""

    api_key: str
    api_key_timeout: int
    api_key_life: str
    id_token: str
    max_assetbar_rows: int

class Preferences(object):
    """Hana3D addon preferences."""

    def __init__(self) -> None:
        """Create a Preferences object."""

    def get(self) -> UserPreferences:
        """Get User Preferences object.

        Returns:
            UserPreferences: user_preferences
        """
        return bpy.context.preferences.addons[HANA3D_NAME].preferences  # noqa: WPS219, E501
