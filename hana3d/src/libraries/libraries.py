"""Libraries functions."""
from contextlib import suppress
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
        if slug == 'slug':
            continue
        prop_library_id = props.custom_props_info[prop_name]['library_id']
        if prop_library_id == library_id:
            custom_props.update({slug: prop_value})
    return custom_props


def get_libraries(props: 'Props'):  # noqa: WPS210
    """Get libraries from asset props.

    Parameters:
        props: Upload or Search Props

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
        if props.asset_type == 'MATERIAL':
            library.update({'slug': props.custom_props[f'{library_name} Slug']})
        with suppress(AttributeError):
            if props.custom_props.keys():
                custom_props = _get_custom_props(props, library_id)
                library.update({'metadata': {'view_props': custom_props}})
        libraries.append(library)
    return libraries


def _set_view_prop(asset_props: 'UploadProps', view_prop: dict, content: str, library: dict):
    name = f'{library.name} {view_prop["name"]}'
    slug = view_prop['slug']
    if name not in asset_props.custom_props:
        asset_props.custom_props_info[name] = {
            'slug': slug,
            'library_name': library.name,
            'library_id': library.id_,
        }
    asset_props.custom_props[name] = content


def set_library_props(libraries: List[dict], asset_props: 'Props'):
    """Set libraries on asset props.

    Parameters:
        libraries: Library dict list
        asset_props: Asset Props
    """
    print(asset_props)
    libraries_list = asset_props.libraries_list
    for asset_library in libraries:
        library = libraries_list[asset_library['name']]
        library.selected = True
        if asset_props.asset_type == 'material':
            view_prop = {
                'name': 'Slug',
                'slug': 'slug'
            }
            _set_view_prop(asset_props, view_prop, asset_library['slug'], library)
            continue
        if not hasattr(asset_props, 'custom_props'):    # noqa: WPS421
            continue
        if 'metadata' in asset_library and asset_library['metadata'] is not None:
            for view_prop in library.metadata['view_props']:
                _set_view_prop(
                    asset_props,
                    view_prop,
                    asset_library['metadata'].get('view_props', {}).get('slug', ''),
                    library,
                )


def _add_library(props: 'Props', library: dict):
    new_library = props.libraries_list.add()
    new_library['name'] = library['name']
    new_library.id_ = library['id']
    metadata = library['metadata']
    if metadata is not None:
        new_library.metadata['library_props'] = metadata['library_props']
        new_library.metadata['view_props'] = metadata['view_props']


def clear_libraries(props: 'Props'):
    """Clear selected libraries.

    Arguments:
        props: hana3d_types.Props,
    """
    props.libraries_list.clear()
    with suppress(AttributeError):
        for name in props.custom_props.keys():
            del props.custom_props[name]    # noqa: WPS420
            del props.custom_props_info[name]   # noqa: WPS420


def update_libraries_list(props: 'Props', context: bpy.types.Context):
    """Update libraries list.

    Arguments:
        props: hana3d_types.Props,
        context: Blender context
    """
    with suppress(KeyError):
        hana3d_profile = context.window_manager[HANA3D_PROFILE]
        unified_props = Unified(context).props
        current_workspace = unified_props.workspace
        previous_libraries = get_libraries(props)
        clear_libraries(props)
        for workspace in hana3d_profile['user']['workspaces']:
            if current_workspace != workspace['id']:
                continue
            for library in workspace['libraries']:
                _add_library(props, library)
        set_library_props(previous_libraries, props)
