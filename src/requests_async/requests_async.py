"""Hana3D requests async."""

import asyncio
import functools
import logging
import uuid

import requests

from ... import hana3d_oauth, logger
from ..preferences.preferences import Preferences


class Request(object):  # noqa : WPS214
    """Hana3D requests async."""

    def __init__(self):
        """Create a Requests object."""
        self.preferences = Preferences()

    async def _request(self, method: str, url: str, **kwargs) -> requests.Response:    # noqa : WPS210
        loop = asyncio.get_event_loop()

        # first normal attempt
        partial = functools.partial(requests.request, method, url, **kwargs)
        response = await loop.run_in_executor(None, partial)

        logging.debug(f'{method.upper()}: {url}')
        logging.debug(response.status_code)

        if not response.ok:
            status_code = response.status_code
            logger.show_report(f'{method} request failed ({status_code}): {response.text}')
            try:
                code = response.json()['code']
            except Exception:
                code = None

            if status_code == 401 and code == 'token_expired':  # noqa : WPS432
                logging.debug('refreshing token')
                logger.show_report(
                    f'Refreshing token. If this fails, login in {HANA3D_DESCRIPTION} Login panel.',
                    10,
                )

                oauth_response = hana3d_oauth.refresh_token()
                updated_headers = self.get_headers(api_key=oauth_response['access_token'])
                kwargs['headers'].update(updated_headers)
                partial = functools.partial(requests.request, method, url, **kwargs)
                response = await loop.run_in_executor(None, partial)
        return response

    async def delete(self, url: str, **kwargs) -> requests.Response:
        """DELETE request.

        Parameters:
            url (str): URL to send request
            kwargs: Arguments for the request

        Returns:
            requests.Response: response
        """
        return await self._request('delete', url, **kwargs)

    async def get(self, url: str, **kwargs) -> requests.Response:
        """GET request.

        Parameters:
            url (str): URL to send request
            kwargs: Arguments for the request

        Returns:
            requests.Response: response
        """
        return await self._request('get', url, **kwargs)

    async def post(self, url: str, **kwargs) -> requests.Response:
        """POST request.

        Parameters:
            url (str): URL to send request
            kwargs: Arguments for the request

        Returns:
            requests.Response: response
        """
        return await self._request('post', url, **kwargs)

    async def put(self, url: str, **kwargs) -> requests.Response:
        """PUT request.

        Parameters:
            url (str): URL to send request
            kwargs: Arguments for the request

        Returns:
            requests.Response: response
        """
        return await self._request('put', url, **kwargs)

    async def patch(self, url: str, **kwargs) -> requests.Response:
        """PATCH request.

        Parameters:
            url (str): URL to send request
            kwargs: Arguments for the request

        Returns:
            requests.Response: response
        """
        return await self._request('patch', url, **kwargs)

    def get_headers(
        self,
        correlation_id: str = None,
        api_key: str = None,
        include_id_token: bool = False,
    ) -> dict:
        """Get Headers for API request.

        Parameters:
            correlation_id (str): The correlation id between multiple requests
            api_key (str): The backend API key
            include_id_token (bool): Determines if the request should include the API id token


        Returns:
            dict: headers
        """
        headers = {
            'accept': 'application/json',
            'X-Request-Id': str(uuid.uuid4()),
        }
        if correlation_id:
            headers['X-Correlation-Id'] = correlation_id
        if api_key is None:
            api_key = self.preferences.get().api_key
        if api_key != '':
            headers['Authorization'] = f'Bearer {api_key}'
        if include_id_token:
            id_token = self.preferences.get().id_token
            headers['X-ID-Token'] = id_token
        return headers
