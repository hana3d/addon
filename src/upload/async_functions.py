import json
import logging
import os

import bpy
import requests

from ... import hana3d_types, logger, paths
from ...config import HANA3D_NAME
from ..requests_async.requests_async import Request, upload_in_chunks
from ..subprocess_async.subprocess_async import Subprocess  # noqa: S404

HANA3D_EXPORT_DATA_FILE = HANA3D_NAME + "_data.json"
CHUNK_SIZE = 1024 * 1024 * 2


async def create_asset(props: hana3d_types.Props, upload_data: dict, correlation_id: str):
    """Send request to create asset.

    Arguments:
        props: Hana3D upload props
        upload_data: Upload data
        correlation_id: Correlation ID
    """
    logger.show_report(props, text='uploading metadata')
    request = Request()
    headers = request.get_headers(correlation_id)

    if props.id == '':
        url = paths.get_api_url('assets')
        try:
            headers = request.get_headers(include_id_token=True)
            response = await request.post(
                url,
                json=upload_data,
                headers=headers,
            )
            logger.show_report(props, text='uploaded metadata')

            dict_response = response.json()
            logging.debug(dict_response)
            props.id = dict_response['id']
        except requests.exceptions.RequestException as e:
            logging.error(e)
            logger.show_report(props, text=str(e))
            props.uploading = False
            return {'CANCELLED'}
    else:
        url = paths.get_api_url('assets', props.id)
        try:
            headers = request.get_headers(include_id_token=True)
            await request.put(
                url,
                json=upload_data,
                headers=headers,
            )
            logger.show_report(props, text='uploaded metadata')
        except requests.exceptions.RequestException as error:
            logging.error(error)
            logger.show_report(props, text=str(error))
            props.uploading = False
            return {'CANCELLED'}


async def create_blend_file(
    props: hana3d_types.Props,
    datafile: str,
    clean_file_path: str,
    filename: str
):
    """Create blend file in a subprocess.

    Arguments:
        props: Hana3D upload props
        datafile: filepath containing the upload data
        clean_file_path: Clean file path
        flename: Name that the blend file will be saved as
    """
    logger.show_report(props, text='creating upload file')
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

    subprocess = Subprocess()

    try:
        result = await subprocess.subprocess(cmd)
        logger.show_report(props, text='created upload file')
        return result
    except Exception as error:
        logging.error(error)
        logger.show_report(props, text=str(error))
        props.uploading = False
        return {'CANCELLED'}


async def get_upload_url(
    props: hana3d_types.Props,
    correlation_id: str,
    upload_data: dict,
    file_: dict
) -> dict:
    """Get upload url from backend.

    Arguments:
        props: Hana3D upload props
        correlation_id: Correlation ID
        upload_data: Upload data
        file_: File information
    """
    logger.show_report(props, text='getting upload url')
    request = Request()
    headers = request.get_headers(correlation_id)
    upload_info = {
        'assetId': upload_data['id'],
        'libraries': upload_data['libraries'],
        'tags': upload_data['tags'],
        'fileType': file_['type'],
        'fileIndex': file_['index'],
        'originalFilename': os.path.basename(file_['file_path']),
        'comment': file_['publish_message']
    }
    if 'workspace' in upload_data:
        upload_info['workspace'] = upload_data['workspace']
    if file_['type'] == 'blend':
        upload_info['viewId'] = upload_data['viewId']
        if 'id_parent' in upload_data:
            upload_info['id_parent'] = upload_data['id_parent']
    upload_create_url = paths.get_api_url('uploads')

    try:
        response = await request.post(upload_create_url, json=upload_info, headers=headers)
        return response.json()
    except requests.exceptions.RequestException as error:
        logging.error(error)
        logger.show_report(props, text=str(error))
        props.uploading = False
        return {'CANCELLED'}


async def upload_file(props: hana3d_types.Props, file_: dict, upload_url: str) -> bool:
    """Upload file.

    Arguments:
        props: Hana3D upload props
        file_: File information
        upload_url: URL to send PUT request
    """
    logger.show_report(props, text='uploading file')
    request = Request()
    uploaded = False
    for a in range(0, 5):
        if not uploaded:
            try:
                upload_response = await request.put(
                    upload_url,
                    data=upload_in_chunks(file_['file_path'], CHUNK_SIZE, file_['type']),
                    stream=True,
                )

                if upload_response.status_code == 200:
                    uploaded = True
                else:
                    logging.error(upload_response.text)
            except Exception as e:
                logging.error(e)
                time.sleep(1)

    return uploaded


async def confirm_upload(
    props: hana3d_types.Props,
    correlation_id: str,
    upload_id: str,
    skip_post_process: str
):
    """Confirm upload to backend.

    Arguments:
        props: Hana3D upload props
        correlation_id: Correlation ID
        upload_id: ID of the upload process
        skip_post_process: Flag to skip the post process in backend
    """
    request = Request()
    headers = request.get_headers(correlation_id)

    upload_done_url = paths.get_api_url(
        'uploads_s3',
        upload_id,
        'upload-file',
        query={'skip_post_process': skip_post_process}
    )
    try:
        upload_response = await request.post(upload_done_url, headers=headers)
    except requests.exceptions.RequestException as error:
        logging.error(error)
        logger.show_report(props, text=str(error))
        props.uploading = False
        return {'CANCELLED'}

    dict_response = upload_response.json()
    if type(dict_response) == dict:
        tempdir = paths.get_temp_dir()
        json_filepath = os.path.join(tempdir, 'post_process.json')
        with open(json_filepath, 'w') as json_file:
            json.dump(dict_response, json_file)


async def finish_asset_creation(props: hana3d_types.Props, correlation_id: str, asset_id: str):
    """Confirm asset creation to backend.

    Arguments:
        props: Hana3D upload props
        correlation_id: Correlation ID
        asset_id: Asset ID
    """
    request = Request()

    confirm_data = {"verificationStatus": "uploaded"}

    url = paths.get_api_url('assets', asset_id)
    headers = request.get_headers(correlation_id)

    try:
        await request.patch(url, json=confirm_data, headers=headers)
    except requests.exceptions.RequestException as error:
        logging.error(error)
        logger.show_report(props, text=str(error))
        props.uploading = False
        return {'CANCELLED'}
