import json
import os
import time

import pytest
import requests

from libs.auth import get_auth
from libs.blender import run_blender_script
from libs.paths import get_addon_name, get_api_url

INSTALL_SCRIPT_PATH = f'{get_addon_name()}/tests/install.py'
CREDENTIALS_SCRIPT_PATH = 'blender_scripts/credentials.py'
UPLOAD_SCRIPT_PATH = 'blender_scripts/upload.py'


def test_upload():
    run_blender_script(
        INSTALL_SCRIPT_PATH
    )
    run_blender_script(
        CREDENTIALS_SCRIPT_PATH
    )
    run_blender_script(
        UPLOAD_SCRIPT_PATH,
        blend_file='scenes/suzanne.blend'
    )


def get_job_id():
    json_filepath = f'{os.path.expanduser("~")}/{get_addon_name()}_data/temp/post_process.json'
    with open(json_filepath, 'r') as json_file:
        data = json.load(json_file)
        return data['post_process_job_id']


def get_headers():
    credentials = get_auth()
    return {'Authorization': f'{credentials["token_type"]} {credentials["access_token"]}'}


def test_post_process():
    job_id = get_job_id()
    url = f'{get_api_url()}/v1/post_product_info?job_id={job_id}'
    headers = get_headers()

    start_time = time.time()

    while time.time() - start_time < 900:
        response = requests.get(url, headers=headers)
        data = response.json()
        if data['status'] == 'processing':
            time.sleep(10)
        elif data['status'] == 'completed':
            return
        elif data['status'] == 'failed':
            pytest.fail(f'Post Process Failed at {data["step"]}')
