"""Auxiliary search async functions."""
import json
import logging
from typing import Dict, Set, Union

import requests

from .query import Query
from .search import get_original_search_results
from ..requests_async.requests_async import Request
from ..ui import colors
from ..ui.main import UI
from ... import paths


async def search_assets(query: Query, options: Dict, ui: UI) -> Union[Dict, Set[str]]:
    """Send request to search assets.

    Arguments:
        query: Search query
        options: Additional parameters
        ui: UI object

    Returns:
        Dict: Search results
        {'CANCELLED'} if it fails
    """
    ui.add_report(text='Searching...')

    request = Request()
    headers = request.get_headers()

    request_data: dict = {}
    request_data['results'] = []

    if options['get_next']:
        try:
            original_data = get_original_search_results()
            urlquery = original_data['next']

            if urlquery is None:
                return {'CANCELLED'}

            urlquery = urlquery.replace('False', 'false').replace('True', 'true')
        except Exception:
            # In case no search results found we don't do next page loading.
            options['get_next'] = False
    else:
        query.save_last_query()
        urlquery = paths.get_api_url('search', query=query.to_dict())

    try:
        logging.debug(urlquery)
        response = await request.get(urlquery, headers=headers)
        dict_response = response.json()
    except requests.exceptions.RequestException as error:
        logging.error(error)
        ui.add_report(text=str(error), color=colors.RED)
        return {'CANCELLED'}

    logging.debug(f'Search assets result: {json.dumps(dict_response)}')
    return dict_response


async def download_thumbnail(image_path: str, url: str):
    """Download thumbnail from url to image_path.

    Parameters:
        image_path: path for saving on the hard drive
        url: link for where the image is hosted
    """
    logging.debug(f'Downloading thumbnail from {url} to {image_path}')
    request = Request()

    response = await request.get(url, stream=False)
    if response.status_code == 200:  # noqa: WPS432
        with open(image_path, 'wb') as image_file:
            image_file.write(response.content)
        logging.debug('Download finished')
