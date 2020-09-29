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
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import List

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


class HTTPAuthRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        if 'code' in self.path:
            self.auth_code = self.path.split('=')[1]
            if self.redirect_url:
                redirect_header = f'''
                    <head>
                        <meta http-equiv="refresh" content="0;url={self.redirect_url}">
                    </head>
                    <script>
                        window.location.href="{self.redirect_url}";
                    </script>
                '''
            else:
                redirect_header = ''
            html_body = f'''
                <html>
                    {redirect_header}
                    <h1>You may now close this window.</h1>
                </html>
            '''
            self.wfile.write(html_body.encode('utf-8'))

            parsed_url = urllib.parse.urlparse(self.path)
            qs = urllib.parse.parse_qs(parsed_url.query)
            self.server.authorization_code = qs['code'][0]
        else:
            self.wfile.write(b'<html><h1>Authorization failed.</h1></html>')


class OAuthAuthenticator:
    def __init__(
            self,
            auth0_url: str,
            platform_url: str,
            client_id: str,
            ports: List[int],
            audience: str):
        self.auth0_url = auth0_url
        self.platform_url = platform_url
        self.client_id = client_id
        self.ports = ports
        self.audience = audience
        self.redirect_uri = ''

    def _get_tokens(
            self,
            authorization_code=None,
            refresh_token=None,
            grant_type='authorization_code'
            # code_verifier=None, # TODO: Uncomment when using PKCE
    ) -> dict:
        data = {'grant_type': grant_type, 'client_id': self.client_id, 'scopes': 'read write'}
        data['redirect_uri'] = self.redirect_uri
        data['code'] = authorization_code
        data['refresh_token'] = refresh_token

        # TODO: Uncomment when using PKCE
        # if code_verifier:
        #     data['code_verifier'] = code_verifier

        response = requests.post(f'{self.auth0_url}/oauth/token/', data=data)
        assert response.ok, \
            f'error retrieving tokens ({response.status_code}), {response.text}'

        return json.loads(response.content)

    def get_new_token(self, redirect_url: str = None) -> str:
        HTTPAuthRequestHandler.redirect_url = redirect_url
        for port in self.ports:
            try:
                httpServer = HTTPServer(('localhost', port), HTTPAuthRequestHandler)
                self.redirect_uri = f'http://localhost:{port}'
                break
            except OSError:
                continue
        else:
            raise Exception(f'Could not create callback endpoint for any ports in {self.ports}')
        # Extra layer of security recommended by auth0 in open source projects
        # TODO: Uncomment when using PKCE
        # key = secrets.token_bytes(32)
        # verifier = base64_URL_encode(key)
        # challenge = base64_URL_encode(sha256(verifier))

        query = {
            'response_type': 'code',
            'scope': 'offline_access openid profile email',
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'audience': self.audience,
            # TODO: Uncomment when using PKCE
            # 'code_challenge': challenge,
            # 'code_challenge_method': 'S256',
        }
        query_string = urllib.parse.urlencode(query)
        authorize_url = f'{self.platform_url}/login?{query_string}'
        webbrowser.open_new(authorize_url)

        httpServer.handle_request()
        authorization_code = httpServer.authorization_code
        # TODO: add code_verifier
        return self._get_tokens(authorization_code=authorization_code)

    def get_refreshed_token(self, refresh_token: str) -> dict:
        return self._get_tokens(refresh_token=refresh_token, grant_type='refresh_token')
