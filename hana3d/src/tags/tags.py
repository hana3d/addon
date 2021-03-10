"""Tags functions."""
from typing import TYPE_CHECKING, List

import bpy

from ..unified_props import Unified
from ...config import HANA3D_PROFILE

if TYPE_CHECKING:
    from ...hana3d_types import Props, UploadProps  # noqa: WPS433


def get_tags(props: 'UploadProps'):
    """Get tags from asset props.

    Parameters:
        props: Upload Props

    Returns:
        libraries: List[str]
    """
    tags: List[str] = []
    for tag in props.tags_list.keys():
        if props.tags_list[tag].selected is True:
            tags.append(tag)
    return tags


def clear_tags(props: 'Props'):
    """Clear tags.

    Arguments:
        props: hana3d_types.Props,
    """
    props.tags_list.clear()


def update_tags_list(props: 'Props', context: bpy.types.Context):
    """Update tags list.

    Arguments:
        props: hana3d_types.Props,
        context: Blender context
    """
    unified_props = Unified(context).props
    previous_tags = get_tags(props)
    clear_tags(props)
    current_workspace = unified_props.workspace
    for workspace in context.window_manager[HANA3D_PROFILE]['user']['workspaces']:
        if current_workspace == workspace['id']:
            for tag in workspace['tags']:
                new_tag = props.tags_list.add()
                new_tag['name'] = tag
    for tag_name in previous_tags:
        props.tags_list[tag_name].selected = True
