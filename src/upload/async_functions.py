"""Auxiliary upload async functions."""
import json
import logging
import os
import subprocess  # noqa: S404
import time
from typing import Set, Union

import bpy
import requests

from ... import hana3d_types, paths
from ...config import HANA3D_NAME
from ..requests_async.requests_async import Request, UploadInChunks
from ..subprocess_async.subprocess_async import Subprocess  # noqa: S404
from ..ui.main import UI

CHUNK_SIZE = 1024 * 1024 * 2


async def create_asset(
    props: hana3d_types.UploadProps,
    ui: UI,
    asset_id: str,
    upload_data: dict,
    correlation_id: str,
) -> Union[str, Set[str]]:
    """Send request to create asset.

    Arguments:
        props: Hana3D upload props
        ui: UI object
        asset_id: Asset ID
        upload_data: Upload data
        correlation_id: Correlation ID

    Returns:
        str: Asset ID
        {'CANCELLED'} if it fails
    """
    ui.add_report(text='Uploading metadata')
    request = Request()
    headers = request.get_headers(correlation_id)

    if asset_id == '':
        url = paths.get_api_url('assets')
        try:
            headers = request.get_headers(include_id_token=True)
            response = await request.post(
                url,
                json=upload_data,
                headers=headers,
            )
            ui.add_report(text='Uploaded metadata')

            dict_response = response.json()
            logging.debug(dict_response)
            return dict_response['id']
        except requests.exceptions.RequestException as error:
            logging.error(error)
            ui.add_report(text=str(error))
            props.uploading = False
            return {'CANCELLED'}
    else:
        url = paths.get_api_url('assets', asset_id)
        try:
            headers = request.get_headers(include_id_token=True)
            await request.put(
                url,
                json=upload_data,
                headers=headers,
            )
            ui.add_report(text='Uploaded metadata')
            return asset_id
        except requests.exceptions.RequestException as err:
            logging.error(err)
            ui.add_report(text=str(err))
            props.uploading = False
            return {'CANCELLED'}


async def create_blend_file(
    props: hana3d_types.UploadProps,
    ui: UI,
    datafile: str,
    clean_file_path: str,
    filename: str,
) -> Union[Set[str], subprocess.CompletedProcess]:
    """Create blend file in a subprocess.

    Arguments:
        props: Hana3D upload props
        ui: UI object
        datafile: filepath containing the upload data
        clean_file_path: Clean file path
        filename: Name that the blend file will be saved as

    Returns:
        Subprocess output
        {'CANCELLED'} if it fails
    """
    ui.add_report(text='Creating upload file')
    binary_path = bpy.app.binary_path
    script_path = os.path.dirname(os.path.realpath(__file__))

    cmd = [
        binary_path,
        '--background',
        '-noaudio',
        clean_file_path,
        '--python',
        os.path.join(script_path, 'upload_bg.py'),
        '--',
        datafile,
        HANA3D_NAME,
        filename,
    ]

    blender_subprocess = Subprocess()

    output = await blender_subprocess.subprocess(cmd)
    ui.add_report(text='Created upload file')
    return output


async def get_upload_url(
    props: hana3d_types.UploadProps,
    ui: UI,
    correlation_id: str,
    upload_data: dict,
    file_info: dict,
) -> Union[Set[str], dict]:
    """Get upload url from backend.

    Arguments:
        props: Hana3D upload props
        ui: UI object
        correlation_id: Correlation ID
        upload_data: Upload data
        file_info: File information

    Returns:
        dict: Request response
        {'CANCELLED'} if it fails
    """
    ui.add_report(text='Getting upload url')
    request = Request()
    headers = request.get_headers(correlation_id)
    upload_info = {
        'assetId': upload_data['id'],
        'libraries': upload_data['libraries'],
        'tags': upload_data['tags'],
        'fileType': file_info['type'],
        'fileIndex': file_info['index'],
        'originalFilename': os.path.basename(file_info['file_path']),
        'comment': file_info['publish_message'],
    }
    upload_info['workspace'] = upload_data.get('workspace')
    if file_info['type'] == 'blend':
        upload_info['viewId'] = upload_data.get('viewId')
        upload_info['id_parent'] = upload_data.get('id_parent')
    upload_create_url = paths.get_api_url('uploads')

    try:
        response = await request.post(upload_create_url, json=upload_info, headers=headers)
        return response.json()
    except requests.exceptions.RequestException as error:
        logging.error(error)
        ui.add_report(text=str(error))
        props.uploading = False
        return {'CANCELLED'}


async def upload_file(ui: UI, file_info: dict, upload_url: str) -> bool:
    """Upload file.

    Arguments:
        ui: UI object
        file_info: File information
        upload_url: URL to send PUT request

    Returns:
        bool: if upload was successful
    """
    ui.add_report(text='Uploading file')
    request = Request()
    uploaded = False
    for index in range(0, 5):
        if not uploaded:
            try:
                upload_response = await request.put(
                    upload_url,
                    data=UploadInChunks(file_info['file_path'], CHUNK_SIZE, file_info['type']),
                    stream=True,
                )

                if upload_response.status_code == 200:  # noqa: WPS432
                    uploaded = True
                else:
                    logging.error(upload_response.text)
            except Exception as error:
                logging.error(f'{index}: {error}')
                time.sleep(1)

    return uploaded


async def confirm_upload(   # noqa: WPS210
    props: hana3d_types.UploadProps,
    ui: UI,
    correlation_id: str,
    upload_id: str,
    skip_post_process: str,
):
    """Confirm upload to backend.

    Arguments:
        props: Hana3D upload props
        ui: UI object
        correlation_id: Correlation ID
        upload_id: ID of the upload process
        skip_post_process: Flag to skip the post process in backend

    Returns:
        {'CANCELLED'} if it fails
    """
    request = Request()
    headers = request.get_headers(correlation_id)

    upload_done_url = paths.get_api_url(
        'uploads_s3',
        upload_id,
        'upload-file',
        query={'skip_post_process': skip_post_process},
    )
    try:
        upload_response = await request.post(upload_done_url, headers=headers)
    except requests.exceptions.RequestException as error:
        logging.error(error)
        ui.add_report(text=str(error))
        props.uploading = False
        return {'CANCELLED'}

    dict_response = upload_response.json()
    if isinstance(dict_response, dict):
        tempdir = paths.get_temp_dir()
        json_filepath = os.path.join(tempdir, 'post_process.json')
        with open(json_filepath, 'w') as json_file:
            json.dump(dict_response, json_file)


async def finish_asset_creation(
    props: hana3d_types.UploadProps,
    ui: UI,
    correlation_id: str,
    asset_id: str,
):
    """Confirm asset creation to backend.

    Arguments:
        props: Hana3D upload props
        ui: UI object
        correlation_id: Correlation ID
        asset_id: Asset ID

    Returns:
        {'CANCELLED'} if it fails
    """
    request = Request()

    confirm_data = {'verificationStatus': 'uploaded'}

    url = paths.get_api_url('assets', asset_id)
    headers = request.get_headers(correlation_id)

    try:
        await request.patch(url, json=confirm_data, headers=headers)
    except requests.exceptions.RequestException as error:
        logging.error(error)
        ui.add_report(text=str(error))
        props.uploading = False
        return {'CANCELLED'}


async def edit_asset(
    ui: UI,
    correlation_id: str,
    asset_id: str,
    asset_data: dict,
):
    """Edit asset data in backend.

    Arguments:
        ui: UI object
        correlation_id: Correlation ID
        asset_id: Asset ID
        asset_data: Data to edit

    Returns:
        {'CANCELLED'} if it fails
    """
    request = Request()

    url = paths.get_api_url('assets', asset_id)
    headers = request.get_headers(correlation_id)

    try:
        await request.put(url, json=asset_data, headers=headers)
    except requests.exceptions.RequestException as error:
        logging.error(error)
        ui.add_report(text=str(error))
        return {'CANCELLED'}


async def edit_view(
    ui: UI,
    correlation_id: str,
    view_id: str,
    view_data: dict,
):
    """Edit view data in backend.

    Arguments:
        ui: UI object
        correlation_id: Correlation ID
        view_id: View ID
        view_data: Data to edit

    Returns:
        {'CANCELLED'} if it fails
    """
    request = Request()

    url = paths.get_api_url('uploads', view_id)
    headers = request.get_headers(correlation_id)

    try:
        await request.put(url, json=view_data, headers=headers)
    except requests.exceptions.RequestException as error:
        logging.error(error)
        ui.add_report(text=str(error))
        return {'CANCELLED'}


async def delete_asset(
    ui: UI,
    asset_id: str,
):
    """Delete asset in backend.

    Arguments:
        ui: UI object
        asset_id: Asset ID

    Returns:
        {'CANCELLED'} if it fails
    """
    request = Request()

    url = paths.get_api_url('assets', asset_id)
    headers = request.get_headers()

    try:
        await request.delete(url, headers=headers)
    except requests.exceptions.RequestException as error:
        logging.error(error)
        ui.add_report(text=str(error))
        return {'CANCELLED'}
