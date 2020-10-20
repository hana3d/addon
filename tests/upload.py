import os
import sys
import time

import requests
import bpy

from hana3d import utils

API_URL = 'https://staging-api.hana3d.com'


def write_tokens(oauth_response: dict):
    preferences = bpy.context.preferences.addons['hana3d'].preferences
    preferences.api_key = oauth_response['access_token']
    preferences.api_key_refresh = ''
    preferences.api_key_timeout = time.time() + oauth_response['expires_in']
    preferences.api_key_life = oauth_response['expires_in']


def test_connection(url: str, headers: dict):
    """Test connection to API"""
    hana3d_response = requests.get(url, headers=headers)
    try:
        assert hana3d_response.json() == 'ok'
    except Exception:
        raise Exception(f'Failed to connect to {url}:\n{hana3d_response.text}')


def get_auth():
    method = 'post'
    url = 'https://hana3d.us.auth0.com/oauth/token'
    headers = {
        'content-type': 'application/json'
    }
    data = {
        "audience": "https://staging-hana3d.com",
        "grant_type": "client_credentials",
        "client_id": os.getenv('CLIENT_ID'),
        "client_secret": os.getenv('CLIENT_SECRET')
    }
    oauth_response = requests.request(method, url, headers=headers, json=data)
    # print(oauth_response.text)
    credentials = oauth_response.json()
    headers = {'Authorization': f'{credentials["token_type"]} {credentials["access_token"]}'}
    test_connection(API_URL, headers)
    write_tokens(credentials)


def main():
    try:
        argv = sys.argv
        if "--" in argv:
            argv = argv[argv.index("--") + 1:]  # get all args after "--"
        else:
            argv = []

        props = utils.get_upload_props()
        print('Upload State: ', props.upload_state)
        print('Uploading: ', props.uploading)

        # get_auth()
        utils.update_profile()

        bpy.ops.object.select_all(action='DESELECT')

        obj = bpy.data.objects['Suzanne']
        obj.select_set(True)
        obj.hana3d.name = 'Suzanne'
        obj.hana3d.publish_message = 'Automated Test'
        obj.hana3d.thumbnail = '//Suzanne.jpg'
        print(obj.hana3d.workspace)
        bpy.ops.object.hana3d_upload(asset_type='MODEL')

        # while props.uploading:
        print('Upload State: ', props.upload_state)
        print('Uploading: ', props.uploading)
        time.sleep(30)

        print('Upload State: ', props.upload_state)

    except Exception as err:
        print(err, file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
