"""Hana3D requests async."""
import functools
import logging
import os
import sys

import requests

from .basic_request import BasicRequest
from ... import hana3d_oauth
from ...config import HANA3D_DESCRIPTION


class UploadInChunks(object):
    """Helper class that creates iterable for uploading file in chunks."""

    def __init__(self, filename: str, chunksize: int = 2 ** 20, report_name: str = 'file'):  # noqa : WPS404,WPS432
        """Create upload in chunks object.

        Parameters:
            filename (str): Name of the file
            chunksize (int): Size of the chunks in bytes
            report_name (str): Report name
        """
        self.filename = filename
        self.chunksize = chunksize
        self.totalsize = os.path.getsize(filename)
        self.readsofar = 0
        self.report_name = report_name

    def __iter__(self):
        """Upload in chunks iterator.

        Yields:
            chunk of file
        """
        with open(self.filename, 'rb') as opened_file:
            while True:
                file_data = opened_file.read(self.chunksize)
                if not file_data:
                    sys.stderr.write('\n')
                    break
                self.readsofar += len(file_data)
                yield file_data

    def __len__(self):
        """Total size of the file.

        Returns:
            int: Total size of the file
        """
        return self.totalsize


class Request(BasicRequest):
    """Hana3D requests async."""

    async def _request(self, method: str, url: str, **kwargs) -> requests.Response:    # noqa : WPS210
        response = await super(Request, self)._request(method, url, **kwargs)

        if not response.ok:
            if status_code == 401 and code == 'token_expired':  # noqa : WPS432
                logging.debug('refreshing token')
                ui.add_report(
                    f'Refreshing token. If this fails, login in {HANA3D_DESCRIPTION} Login panel.',
                    10,
                )

                oauth_response = hana3d_oauth.refresh_token()
                updated_headers = self.get_headers(api_key=oauth_response['access_token'])
                kwargs['headers'].update(updated_headers)
                partial = functools.partial(requests.request, method, url, **kwargs)
                response = await loop.run_in_executor(None, partial)
        return response
