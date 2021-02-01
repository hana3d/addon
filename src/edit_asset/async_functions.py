"""Auxiliary edit async functions."""
import logging

import requests

from ..requests_async.requests_async import Request
from ..ui.main import UI
from ... import paths


async def edit_asset(
    ui: UI,
    correlation_id: str,
    asset_id: str,
    asset_data: dict,
):
    """Edit asset data in backend.

    Arguments:
        ui: UI object
        correlation_id: Correlation ID
        asset_id: Asset ID
        asset_data: Data to edit

    Returns:
        {'CANCELLED'} if it fails
    """
    request = Request()

    url = paths.get_api_url('assets', asset_id)
    headers = request.get_headers(correlation_id)

    try:
        await request.put(url, json=asset_data, headers=headers)
    except requests.exceptions.RequestException as error:
        logging.error(error)
        ui.add_report(text=str(error))
        return {'CANCELLED'}


async def edit_view(
    ui: UI,
    correlation_id: str,
    view_id: str,
    view_data: dict,
):
    """Edit view data in backend.

    Arguments:
        ui: UI object
        correlation_id: Correlation ID
        view_id: View ID
        view_data: Data to edit

    Returns:
        {'CANCELLED'} if it fails
    """
    request = Request()

    url = paths.get_api_url('uploads', view_id)
    headers = request.get_headers(correlation_id)

    try:
        await request.put(url, json=view_data, headers=headers)
    except requests.exceptions.RequestException as error:
        logging.error(error)
        ui.add_report(text=str(error))
        return {'CANCELLED'}


async def delete_asset(
    ui: UI,
    asset_id: str,
):
    """Delete asset in backend.

    Arguments:
        ui: UI object
        asset_id: Asset ID

    Returns:
        {'CANCELLED'} if it fails
    """
    request = Request()

    url = paths.get_api_url('assets', asset_id)
    headers = request.get_headers()

    try:
        await request.delete(url, headers=headers)
    except requests.exceptions.RequestException as error:
        logging.error(error)
        ui.add_report(text=str(error))
        return {'CANCELLED'}
