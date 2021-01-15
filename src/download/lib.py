import os
import shutil

from ... import paths


def check_existing(asset_data):
    ''' check if the object exists on the hard drive'''
    file_names = paths.get_download_filenames(asset_data)

    if len(file_names) == 2:
        # TODO this should check also for failed or running downloads.
        # If download is running, assign just the running thread.
        # if download isn't running but the file is wrong size,
        #  delete file and restart download (or continue downoad? if possible.)
        if os.path.isfile(file_names[0]) and not os.path.isfile(file_names[1]):
            shutil.copy(file_names[0], file_names[1])
        # only in case of changed settings or deleted/moved global dict.
        elif not os.path.isfile(file_names[0]) and os.path.isfile(file_names[1]):
            shutil.copy(file_names[1], file_names[0])

    if len(file_names) == 0 or not os.path.isfile(file_names[0]):
        return False

    newer_asset_in_server = (
        asset_data.get('created') is not None
        and float(asset_data['created']) > float(os.path.getctime(file_names[0]))
    )
    if newer_asset_in_server:
        os.remove(file_names[0])
        return False

    return True
