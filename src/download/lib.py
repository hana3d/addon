"""Helper methods for asset download."""
import os
import shutil

from ..search.search import SearchResult
from ... import paths


def newer_asset_in_server(asset_data: SearchResult, file_name: str) -> bool:
    """Check if there is a newer version of the asset in the server.

    Parameters:
        asset_data: Asset Data
        file_name: path to file in the hard drive

    Returns:
        bool: True if there is a newer version, False otherwise
    """
    return (
        asset_data.created is not None
        and float(asset_data.created) > float(os.path.getctime(file_name))
    )


def copy_file(source: str, target: str):
    """Copy source file to target file if source exists and target does not.

    Parameters:
        source: path to file to be copied
        target: path to file that will be written
    """
    if os.path.isfile(source) and not os.path.isfile(target):
        shutil.copy(source, target)


def check_existing(asset_data: SearchResult) -> bool:
    """Check if the object exists on the hard drive.

    Parameters:
        asset_data: Asset Data

    Returns:
        bool: True if the object exists, False otherwise
    """
    file_names = paths.get_download_filenames(asset_data)

    if len(file_names) == 2:
        copy_file(file_names[0], file_names[1])  # noqa: WPS204
        copy_file(file_names[1], file_names[0])

    if not file_names or not os.path.isfile(file_names[0]):
        return False

    if newer_asset_in_server(asset_data, file_names[0]):
        os.remove(file_names[0])
        return False

    return True
