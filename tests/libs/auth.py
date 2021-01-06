import os

import requests

from libs.paths import get_api_url, get_audience_url


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
        "audience": get_audience_url(),
        "grant_type": "client_credentials",
        "client_id": os.getenv('CLIENT_ID'),
        "client_secret": os.getenv('CLIENT_SECRET')
    }
    oauth_response = requests.request(method, url, headers=headers, json=data)
    credentials = oauth_response.json()
    headers = {'Authorization': f'{credentials["token_type"]} {credentials["access_token"]}'}
    test_connection(get_api_url(), headers)

    return credentials
