# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####


import json
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

import requests

# TODO: Uncomment when using PKCE
# import base64
# import hashlib
# import secrets
# from urllib.parse import quote as urlquote
# def base64_URL_encode(bytes_URL: bytes) -> str:
#     URL = base64.urlsafe_b64encode(bytes_URL)
#     return (
#         str(URL, 'utf-8')
#         .replace('=', '')
#     )
# def sha256(buffer: str) -> bytes:
#     buffer_bytes = buffer.encode('utf-8')
#     m = hashlib.sha256()
#     m.update(buffer_bytes)
#     return m.digest()


class SimpleOAuthAuthenticator(object):
    def __init__(self, auth0_url, platform_url, client_id, ports, audience):
        self.auth0_url = auth0_url
        self.platform_url = platform_url
        self.client_id = client_id
        self.ports = ports
        self.audience = audience

    def _get_tokens(
        self,
        authorization_code=None,
        refresh_token=None,
        grant_type='authorization_code'
        # code_verifier=None, # TODO: Uncomment when using PKCE
    ):
        data = {'grant_type': grant_type, 'client_id': self.client_id, 'scopes': 'read write'}
        if hasattr(self, 'redirect_uri'):
            data['redirect_uri'] = self.redirect_uri
        if authorization_code:
            data['code'] = authorization_code
        if refresh_token:
            data['refresh_token'] = refresh_token

        # TODO: Uncomment when using PKCE
        # if code_verifier:
        #     data['code_verifier'] = code_verifier

        response = requests.post(f'{self.auth0_url}/oauth/token/', data=data)
        if response.status_code != 200:
            print(f'error retrieving refresh tokens {response.status_code}')
            print(response.content)
            return None, None, None

        response_json = json.loads(response.content)
        refresh_token = response_json['refresh_token']
        access_token = response_json['access_token']
        return access_token, refresh_token, response_json

    def get_new_token(self, redirect_url=None):
        class HTTPServerHandler(BaseHTTPRequestHandler):
            html_template = '<html>%(head)s<h1>%(message)s</h1></html>'

            def do_GET(self):
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                if 'code' in self.path:
                    self.auth_code = self.path.split('=')[1]
                    # Display to the user that they no longer need the browser window
                    if redirect_url:
                        redirect_string = (
                            '<head><meta http-equiv="refresh" content="0;url=%(redirect_url)s"></head>'  # noqa E501
                            '<script> window.location.href="%(redirect_url)s"; </script>' % {'redirect_url': redirect_url}  # noqa E501
                        )
                    else:
                        redirect_string = ''
                    self.wfile.write(
                        bytes(
                            self.html_template
                            % {
                                'head': redirect_string,
                                'message': 'You may now close this window.',
                            },
                            'utf-8',
                        )
                    )
                    qs = parse_qs(urlparse(self.path).query)
                    self.server.authorization_code = qs['code'][0]
                else:
                    self.wfile.write(
                        bytes(
                            self.html_template % {'head': '', 'message': 'Authorization failed.'},
                            'utf-8',
                        )
                    )

        for port in self.ports:
            try:
                httpServer = HTTPServer(('localhost', port), HTTPServerHandler)
            except OSError:
                continue
            break

        # Extra layer of security recommended by auth0 in open source projects
        # TODO: Uncomment when using PKCE
        # key = secrets.token_bytes(32)
        # verifier = base64_URL_encode(key)
        # challenge = base64_URL_encode(sha256(verifier))

        self.redirect_uri = f'http://localhost:{port}'
        authorize_url = (
            f'{self.platform_url}/login'
            + '?response_type=code'
            + '&scope=offline_access openid profile email'
            + f'&client_id={self.client_id}'
            + f'&redirect_uri={self.redirect_uri}'
            + f'&audience={self.audience}'
            # + f'&code_challenge={challenge}' # TODO: Uncomment when using PKCE
            # + f'&code_challenge_method=S256'
        )
        webbrowser.open_new(authorize_url)

        httpServer.handle_request()
        authorization_code = httpServer.authorization_code
        # TODO: add code_verifier
        return self._get_tokens(authorization_code=authorization_code)

    def get_refreshed_token(self, refresh_token):
        return self._get_tokens(refresh_token=refresh_token, grant_type='refresh_token')
