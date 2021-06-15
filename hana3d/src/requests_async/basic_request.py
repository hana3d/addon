"""Hana3D requests async."""
import asyncio
import functools
import logging
import uuid

import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

from ..preferences.preferences import Preferences
from ..ui import colors
from ..ui.main import UI


class BasicRequest(object):  # noqa : WPS214
    """Hana3D requests async."""

    def __init__(self):
        """Create a Requests object."""
        self.preferences = Preferences()
        retry_strategy = Retry(
            total=5,
            status_forcelist=[429, 500, 502, 503, 504],
            method_whitelist=['DELETE', 'GET', 'POST', 'PUT', 'PATCH'],
            backoff_factor=0.1,
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session = requests.Session()
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)

    async def _request(self, method: str, url: str, **kwargs) -> requests.Response:    # noqa : WPS210
        loop = asyncio.get_event_loop()

        partial = functools.partial(self.session.request, method, url, **kwargs)
        response = await loop.run_in_executor(None, partial)

        logging.debug(f'{method.upper()} {url} ({response.status_code})')  # noqa : WPS221

        if not response.ok:
            status_code = response.status_code
            ui = UI()
            ui.add_report(
                f'{method} request failed ({status_code}): {response.text}',
                color=colors.RED,
            )

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
