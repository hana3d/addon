"""Libraries functions."""
from typing import TYPE_CHECKING, List

import bpy

from ..unified_props import Unified
from ...config import HANA3D_PROFILE

if TYPE_CHECKING:
    from ...hana3d_types import Props, UploadProps  # noqa: WPS433


def _get_custom_props(props: 'UploadProps', library_id: str):
    custom_props = {}
    for prop_name in props.custom_props.keys():
        prop_value = props.custom_props[prop_name]
        slug = props.custom_props_info[prop_name]['slug']
        prop_library_id = props.custom_props_info[prop_name]['library_id']
        if prop_library_id == library_id:
            custom_props.update({slug: prop_value})
    return custom_props


def get_libraries(props: 'UploadProps'):  # noqa: WPS210
    """Get libraries from asset props.

    Parameters:
        props: Upload Props

    Returns:
        libraries: List[dict]
    """
    libraries: List[dict] = []
    for library_name in props.libraries_list.keys():
        if props.libraries_list[library_name].selected is not True:
            continue
        library_id = props.libraries_list[library_name].id_
        library = {}
        library.update({
            'name': library_name,
            'id': library_id,
        })
        if props.custom_props.keys():
            custom_props = _get_custom_props(props, library_id)
            library.update({'metadata': {'view_props': custom_props}})
        libraries.append(library)
    return libraries


def _set_view_prop(asset_props: 'UploadProps', view_prop: dict, library: dict, metadata: dict):
    name = f'{library.name} {view_prop["name"]}'
    slug = view_prop['slug']
    if name not in asset_props.custom_props:
        asset_props.custom_props_info[name] = {
            'slug': slug,
            'library_name': library.name,
            'library_id': library.id_,
        }
    if 'view_props' in metadata and slug in metadata['view_props']:
        asset_props.custom_props[name] = metadata['view_props'][slug]
    else:
        asset_props.custom_props[name] = ''


def set_library_props(libraries: List[dict], asset_props: 'UploadProps'):
    """Set libraries on asset props.

    Parameters:
        asset_data: Asset Data
        asset_props: Asset Props
    """
    libraries_list = asset_props.libraries_list
    for asset_library in libraries:
        library = libraries_list[asset_library['name']]
        library.selected = True
        if 'metadata' in asset_library and asset_library['metadata'] is not None:
            for view_prop in library.metadata['view_props']:
                _set_view_prop(asset_props, view_prop, library, asset_library['metadata'])


def _add_library(props: 'Props', library: dict):
    new_library = props.libraries_list.add()
    new_library['name'] = library['name']
    new_library.id_ = library['id']
    metadata = library['metadata']
    if metadata is not None:
        new_library.metadata['library_props'] = metadata['library_props']
        new_library.metadata['view_props'] = metadata['view_props']


def update_libraries_list(props: 'Props', context: bpy.types.Context):
    """Update libraries list.

    Arguments:
        props: hana3d_types.Props,
        context: Blender context
    """
    unified_props = Unified(context).props
    current_workspace = unified_props.workspace
    previous_libraries = get_libraries(props)
    props.libraries_list.clear()
    if hasattr(props, 'custom_props'):  # noqa: WPS421
        for name in props.custom_props.keys():
            del props.custom_props[name]    # noqa: WPS420
            del props.custom_props_info[name]   # noqa: WPS420
    for workspace in context.window_manager[HANA3D_PROFILE]['user']['workspaces']:
        if current_workspace != workspace['id']:
            continue
        for library in workspace['libraries']:
            _add_library(props, library)
    set_library_props(previous_libraries, props)
