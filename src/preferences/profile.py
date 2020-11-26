"""Hana3D Profile."""
import logging

import bpy

from ... import config, paths, rerequests, tasks_queue


class Profile(object):
    """Hana3D user profile."""

    def __init__(self):
        """Create a Profile object."""

    def get(self):
        """Get User Profile object.

        Returns:
            dict: user_profile
        """
        return bpy.context.window_manager.get(config.HANA3D_PROFILE)

    def update_async(self):
        """Update the User Profile asynchronously."""
        tasks_queue.add_task(self._update_async_task)

    def _update_async_task(self):
        """Task to Update the User Profile asynchronously."""
        logging.info('update_profile')  # noqa: WPS421
        url = paths.get_api_url('me')
        headers = rerequests.get_headers(include_id_token=True)
        response = rerequests.get(url, headers=headers)

        if not response.ok:
            logging.error(f'Failed to get profile data: {response.text}')  # noqa: WPS421

        bpy.context.window_manager[config.HANA3D_PROFILE] = response.json()
