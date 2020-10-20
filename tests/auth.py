import os
import sys
import time

import bpy
import requests

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
    credentials = oauth_response.json()
    headers = {'Authorization': f'{credentials["token_type"]} {credentials["access_token"]}'}
    test_connection(API_URL, headers)
    write_tokens(credentials)


def main():
    try:
        get_auth()
        bpy.ops.wm.save_userpref()

    except Exception as err:
        print(err, file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
