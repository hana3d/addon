"""Tags functions."""
from typing import TYPE_CHECKING, List

import bpy

from ...config import HANA3D_PROFILE
from ..unified_props import Unified

if TYPE_CHECKING:
    from ...hana3d_types import Props, UploadProps  # noqa: WPS433


def get_tags(props: 'UploadProps'):
    """Get tags from asset props.

    Parameters:
        props: Upload Props
    """
    tags: List[str] = []
    for tag in props.tags_list.keys():
        if props.tags_list[tag].selected is True:
            tags.append(tag)
    return tags


def update_tags_list(props: 'Props', context: bpy.types.Context):
    """Update tags list.

    Arguments:
        props: hana3d_types.Props,
        context: Blender context
    """
    unified_props = Unified(context).props
    props.tags_list.clear()
    current_workspace = unified_props.workspace
    for workspace in context.window_manager[HANA3D_PROFILE]['user']['workspaces']:
        if current_workspace == workspace['id']:
            for tag in workspace['tags']:
                new_tag = props.tags_list.add()
                new_tag['name'] = tag
