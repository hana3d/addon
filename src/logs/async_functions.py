"""Auxiliary log async functions."""
import logging

from requests.exceptions import RequestException

from ..requests_async.requests_async import Request
from ..ui.main import UI
from ... import paths


async def send_logs(ui: UI, correlation_id: str, issue_key: str, filepath: str):
    """Send logs to backend.

    Parameters:
        ui: UI object
        correlation_id: Correlation ID
        issue_key: Key of the issue on Hana3D Support Desk
        filepath: Path to log file

    Returns:
        {'CANCELLED'} if it fails
    """
    request = Request()

    url = paths.get_api_url('send_logs')
    logging.debug(f'Sending logs from {issue_key} in {filepath} to {url}')
    headers = request.get_headers(correlation_id)

    try:
        with open(filepath, 'rb') as log_file:
            file_content = log_file.read()
            request_data = {
                'data': file_content,
                'issue_key': issue_key,
            }
            await request.post(url, json=request_data, headers=headers)
    except RequestException as error:
        logging.error(error)
        ui.add_report(text=str(error))
        return {'CANCELLED'}
