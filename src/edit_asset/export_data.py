"""Auxiliary data manipulation functions."""
from ..libraries.libraries import get_libraries
from ..tags.tags import get_tags
from ... import hana3d_types


def get_edit_data(props: hana3d_types.UploadProps):
    """Get data to edit asset and view.

    Arguments:
        props: Hana3D upload props

    Returns:
        asset_data, view_data
    """
    asset_data = {
        'name': props.name,
        'description': props.description,
    }
    view_data = {
        'name': props.name,
    }
    view_data['tags'] = get_tags(props)
    view_data['libraries'] = get_libraries(props)

    return asset_data, view_data
