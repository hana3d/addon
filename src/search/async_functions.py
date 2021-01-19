"""Auxiliary search async functions."""
import json
import logging
import os
from typing import Dict, Set, Union

import requests

from .query import Query
from ..ui.main import UI
from ... import paths, rerequests


async def search_assets(
    query: Query,
    params: Dict,
    ui: UI
) -> Union[Dict, Set[str]]:
    """Sends request to search assets.

    Arguments:
        query: Search query
        params: Additional parameters
        ui: UI object

    Returns:
        Dict: Search results
        {'CANCELLED'} if it fails
    """
    ui.add_report(text='Searching...')

    tempdir = paths.get_temp_dir(f'{query.asset_type}_search')
    json_filepath = os.path.join(tempdir, f'{query.asset_type}_searchresult.json')

    headers = rerequests.get_headers()

    request_data : dict = {}
    request_data['results'] = []

    if params['get_next']:
        with open(json_filepath, 'r') as infile:
            try:
                original_data = json.load(infile)
                urlquery = original_data['next']
                urlquery = urlquery.replace('False', 'false').replace('True', 'true')

                if urlquery is None:
                    return {'CANCELLED'}
            except Exception:
                # In case no search results found on drive we don't do next page loading.
                params['get_next'] = False
    if not params['get_next']:
        query.save_last_query()
        urlquery = paths.get_api_url('search', query=query.to_dict())
    
    try:
        logging.debug(urlquery)
        request = rerequests.get(urlquery, headers=headers)
    except requests.exceptions.RequestException as e:
        logging.error(e)
        ui.add_report(text=str(e))
        return {'CANCELLED'}
    logging.debug('Response is back ')
    try:
        request_data = request.json()
        request_data['status_code'] = request.status_code
    except Exception as inst:
        logging.error(inst)
        ui.add_report(text=request.text)
        return {'CANCELLED'}

    return request_data


async def download_thumbnail(image_path: str, url: str):
    request = rerequests.get(url, stream=False)
    if request.status_code == 200:
        with open(image_path, 'wb') as f:
            f.write(request.content)
