"""Hana3D Profile."""
import logging
from pathlib import Path
from typing import TYPE_CHECKING

import bpy

import bugsnag
import sentry_sdk

from ..requests_async.basic_request import BasicRequest
from ..search.search import get_search_props
from ..unified_props import Unified
from ..upload.upload import get_upload_props
from ... import config, paths

if TYPE_CHECKING:
    from ...hana3d_types import Props  # noqa: WPS433

def configure_bugsnag(api_key: str):
    """Configure bugsnag.

    Arguments:
        api_key: str
    """
    bugsnag.configure(
        api_key=api_key,
        project_root=Path(__file__).parent.parent.parent,
    )


def configure_sentry(url: str):
    """Configure sentry.

    Arguments:
        url: str
    """
    sentry_sdk.init(
        url,
        traces_sample_rate=1.0,
    )


def update_tags_list(props: 'Props', context: bpy.types.Context):
    """Update tags list.

    Arguments:
        props: hana3d_types.Props,
        context: Blender context
    """
    unified_props = Unified(context).props
    props.tags_list.clear()
    current_workspace = unified_props.workspace
    for workspace in context.window_manager[config.HANA3D_PROFILE]['user']['workspaces']:
        if current_workspace == workspace['id']:
            for tag in workspace['tags']:
                new_tag = props.tags_list.add()
                new_tag['name'] = tag


def update_libraries_list(props: 'Props', context: bpy.types.Context):
    """Update libraries list.

    Arguments:
        props: hana3d_types.Props,
        context: Blender context
    """
    unified_props = Unified(context).props
    props.libraries_list.clear()
    if hasattr(props, 'custom_props'):  # noqa: WPS421
        for name in props.custom_props.keys():
            del props.custom_props[name]    # noqa: WPS420
            del props.custom_props_info[name]   # noqa: WPS420
    current_workspace = unified_props.workspace
    for workspace in context.window_manager[config.HANA3D_PROFILE]['user']['workspaces']:
        if current_workspace == workspace['id']:
            for library in workspace['libraries']:
                new_library = props.libraries_list.add()
                new_library['name'] = library['name']
                new_library.id_ = library['id']
                if library['metadata'] is not None:
                    new_library.metadata['library_props'] = library['metadata']['library_props']
                    new_library.metadata['view_props'] = library['metadata']['view_props']


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

        window_manager = bpy.context.window_manager
        window_manager[config.HANA3D_PROFILE] = response.json()

        search_props = get_search_props()
        update_libraries_list(search_props, bpy.context)
        update_tags_list(search_props, bpy.context)

        upload_props = get_upload_props()
        update_libraries_list(upload_props, bpy.context)
        update_tags_list(upload_props, bpy.context)

        configure_bugsnag(window_manager[config.HANA3D_PROFILE]['user']['bugsnag_key'])
        configure_sentry(window_manager[config.HANA3D_PROFILE]['user']['sentry_url'])
