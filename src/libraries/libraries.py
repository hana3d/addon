"""Libraries functions."""
from typing import TYPE_CHECKING, List

import bpy

from ...config import HANA3D_PROFILE
from ..unified_props import Unified

if TYPE_CHECKING:
    from ...hana3d_types import Props, UploadProps  # noqa: WPS433


def get_libraries(props: 'UploadProps'):  # noqa: WPS210
    """Get libraries from asset props.

    Parameters:
        props: Upload Props
    """
    libraries: List[dict] = []
    for library_name in props.libraries_list.keys():
        if props.libraries_list[library_name].selected is True:
            library_id = props.libraries_list[library_name].id_
            library = {}
            library.update({
                'id': library_id,
            })
            if props.custom_props.keys():
                custom_props = {}
                for prop_name in props.custom_props.keys():
                    prop_value = props.custom_props[prop_name]
                    slug = props.custom_props_info[prop_name]['slug']
                    prop_library_id = props.custom_props_info[prop_name]['library_id']
                    if prop_library_id == library_id:
                        custom_props.update({slug: prop_value})  # noqa: WPS220
                library.update({'metadata': {'view_props': custom_props}})
            libraries.append(library)
    return libraries


def set_library_props(asset_data, asset_props):
    """Set libraries on asset props.

    Parameters:
        asset_data: Asset Data
        asset_props: Asset Props
    """
    update_libraries_list(asset_props, bpy.context)
    libraries_list = asset_props.libraries_list
    for asset_library in asset_data.libraries:
        library = libraries_list[asset_library['name']]
        library.selected = True
        if 'metadata' in asset_library and asset_library['metadata'] is not None:
            for view_prop in library.metadata['view_props']:
                name = f'{library.name} {view_prop["name"]}'
                slug = view_prop['slug']
                if name not in asset_props.custom_props:
                    asset_props.custom_props_info[name] = {
                        'slug': slug,
                        'library_name': library.name,
                        'library_id': library.id_,
                    }
                if 'view_props' in asset_library['metadata'] and slug in asset_library['metadata']['view_props']:  # noqa: E501
                    asset_props.custom_props[name] = asset_library['metadata']['view_props'][slug]
                else:
                    asset_props.custom_props[name] = ''


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
    for workspace in context.window_manager[HANA3D_PROFILE]['user']['workspaces']:
        if current_workspace == workspace['id']:
            for library in workspace['libraries']:
                new_library = props.libraries_list.add()
                new_library['name'] = library['name']
                new_library.id_ = library['id']
                if library['metadata'] is not None:
                    new_library.metadata['library_props'] = library['metadata']['library_props']
                    new_library.metadata['view_props'] = library['metadata']['view_props']
