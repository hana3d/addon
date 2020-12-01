"""Hana3D Profile."""
import bpy

from ..requests_async.requests_async import Request
from ... import config, paths, rerequests


class Profile(object):
    """Hana3D user profile."""

    def __init__(self):
        """Create a Profile object."""

    def get(self) -> dict:
        """Get User Profile object.

        Returns:
            dict: user_profile
        """
        return bpy.context.window_manager.get(config.HANA3D_PROFILE)

    async def update_async(self) -> None:
        """Update the User Profile asynchronously."""`
        request = Request()
        print('update_profile')  # noqa: WPS421
        url = paths.get_api_url('me')
        headers = requests.get_headers(include_id_token=True)
        await request.get(url, headers=headers)

        if not response.ok:
            print(f'Failed to get profile data: {response.text}')  # noqa: WPS421

        bpy.context.window_manager[config.HANA3D_PROFILE] = response.json()
