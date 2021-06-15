"""Hana3D Profile."""
import logging

import bpy

import sentry_sdk

from ..libraries.libraries import update_libraries_list
from ..requests_async.basic_request import BasicRequest
from ..search.search import get_search_props
from ..tags.tags import update_tags_list
from ..upload.upload import get_upload_props
from ... import config, paths
from ...utils import get_addon_version


def configure_sentry(url: str):
    """Configure sentry.

    Arguments:
        url: str
    """
    sentry_sdk.init(
        url,
        traces_sample_rate=1.0,
        release='.'.join(map(str, get_addon_version())),
        send_default_pii=True,
    )


class Profile(object):
    """Hana3D user profile."""

    def __init__(self) -> None:
        """Create a Profile object."""

    def get(self) -> dict:
        """Get User Profile object.

        Returns:
            dict: user_profile
        """
        return bpy.context.window_manager.get(config.HANA3D_PROFILE)

    async def update_async(self) -> None:
        """Update the User Profile asynchronously."""
        request = BasicRequest()
        logging.info('update_profile')  # noqa: WPS421
        url = paths.get_api_url('me')
        headers = request.get_headers(include_id_token=True)
        response = await request.get(url, headers=headers)

        if not response.ok:
            logging.error(f'Failed to get profile data: {response.text}')  # noqa: WPS421
            return

        window_manager = bpy.context.window_manager
        window_manager[config.HANA3D_PROFILE] = response.json()

        search_props = get_search_props()
        update_libraries_list(search_props, bpy.context)
        update_tags_list(search_props, bpy.context)

        upload_props = get_upload_props()
        update_libraries_list(upload_props, bpy.context)
        update_tags_list(upload_props, bpy.context)

        configure_sentry(window_manager[config.HANA3D_PROFILE]['user']['sentry_url'])
