"""Auxiliary search async functions."""
import asyncio
import json
import logging
import os
from typing import Dict

import requests

from .query import Query
from .search import get_original_search_results
from ..requests_async.requests_async import Request
from ..ui import colors
from ..ui.main import UI
from ... import paths


async def search_assets(query: Query, options: Dict, ui: UI) -> Dict:
    """Send request to search assets.

    Arguments:
        query: Search query
        options: Additional parameters
        ui: UI object

    Returns:
        Dict: Search results

    Raises:
        Exception: When get_next flag is sent with no previous search results
        request_error: When cannot retrieve results from API
    """
    request = Request()
    headers = request.get_headers()

    request_data: dict = {}
    request_data['results'] = []

    if options['get_next']:
        original_data = get_original_search_results()
        urlquery = original_data.get('next', None)

        if urlquery is None:
            options['get_next'] = False
            logging.error('Could not retrieve url for next results')
            raise Exception('No next url found')

        urlquery = urlquery.replace('False', 'false').replace('True', 'true')
    else:
        query.save_last_query()
        urlquery = paths.get_api_url('search', query=query.to_dict())

    try:
        logging.debug(urlquery)
        response = await request.get(urlquery, headers=headers)
        dict_response = response.json()
    except requests.exceptions.RequestException as request_error:
        logging.error(request_error)
        ui.add_report(text=str(request_error), color=colors.RED)
        raise request_error

    logging.debug(f'Search assets result: {json.dumps(dict_response)}')
    return dict_response


def _read_chunk(iterator):
    try:
        return next(iterator)
    except Exception:
        return b''


async def download_thumbnail(image_path: str, url: str):
    """Download thumbnail from url to image_path.

    Parameters:
        image_path: path for saving on the hard drive
        url: link for where the image is hosted
    """
    logging.debug(f'Downloading thumbnail from {url} to {image_path}')
    request = Request()

    response = await request.get(url, stream=False)
    if response.status_code != 200:  # noqa: WPS432
        logging.error('Could not download thumbnail')
        return

    tmp_file_name = f'{image_path}_tmp'
    with open(tmp_file_name, 'wb') as tmp_file:
        total_length = response.headers.get('Content-Length')

        if total_length is None:  # no content length header
            tmp_file.write(response.content)
        else:
            chunk_size = 500 * 1000  # noqa: WPS432
            iterator = response.iter_content(chunk_size=chunk_size)
            loop = asyncio.get_event_loop()
            while True:
                download_data = await loop.run_in_executor(None, _read_chunk, iterator)
                if not download_data:
                    tmp_file.close()
                    break
                tmp_file.write(download_data)

    os.rename(tmp_file_name, image_path)
    logging.debug('Download finished')
