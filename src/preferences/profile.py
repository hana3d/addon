"""Hana3D Profile."""
import logging
from typing import TYPE_CHECKING

import bpy

from ..requests_async.basic_request import BasicRequest
from ..search.search import Search
from ..upload.upload import get_upload_props
from ... import config, paths

if TYPE_CHECKING:
    from ...hana3d_types import Props   # noqa: WPS433


def update_tags_list(props: 'Props', context: bpy.types.Context):
    """Update tags list.

    Arguments:
        props: hana3d_types.Props,
        context: Blender context
    """
    props.tags_list.clear()
    current_workspace = props.workspace
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
    props.libraries_list.clear()
    current_workspace = props.workspace
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

        bpy.context.window_manager[config.HANA3D_PROFILE] = response.json()

        search = Search(bpy.context)

        update_libraries_list(search.props, bpy.context)
        update_tags_list(search.props, bpy.context)

        upload_props = get_upload_props()
        update_libraries_list(upload_props, bpy.context)
        update_tags_list(upload_props, bpy.context)
