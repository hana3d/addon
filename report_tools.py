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

import datetime
import functools
import json
import logging
import pprint
import traceback

HEADERS = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Credentials': True,
    'Content-Type': 'application/json'
}


class ResponseEncoder(json.JSONEncoder):
    """JSONEncoder with additional logic for encoding non-standard objects"""

    def default(self, obj):
        if isinstance(obj, (datetime.date, datetime.datetime, datetime.time)):
            return obj.isoformat()
        if isinstance(obj, requests.Response):
            try:
                return obj.json()
            except json.JSONDecodeError:
                return obj.text
        return super().default(obj)


def format_exception(exc: Exception) -> dict:
    if len(exc.args) == 1 and isinstance(exc.args[0], dict):
        error_msg = exc.args[0]
    else:
        error_msg = ';'.join(str(arg) for arg in exc.args)
    return {
        'errorMessage': error_msg,
        'errorType': exc.__class__.__name__,
        'stackTrace': traceback.format_exc()
    }


def format_message(json_msg):
    json_msg = json.loads(json_msg)
    json_msg = pprint.pformat(json_msg, width=999)
    json_msg = json_msg.replace("'", "")
    json_msg = json_msg.replace("\\n", "")
    return json_msg


def send_to_slack(status_code: int, json_body: dict):
    msg = format_message(json_body)
    print(msg)
    # json = {"text": f"An HTTP {status_code} error has occurred:\n {msg}"}
    # requests.post(config.HANA3D_ERRORS_WEBHOOK_URL, json=json)


def report_wrapper(func):
    """Decorator to build error reports"""
    @functools.wraps(func)
    def wrapper(event, context):
        encoder = ResponseEncoder()
        try:
            logging.debug(event, extra={'type': 'debug_event'})
            body = func(event, context)
            if body is None:
                body = 'ok'
            status_code = 200
            json_body = encoder.encode(body)
            payload = {
                'statusCode': status_code,
                'headers': HEADERS,
                'body': json_body
            }
            logging.debug(payload, extra={'type': 'debug_response'})
        except Exception as e:
            logging.exception(e)
            body = format_exception(e)
            status_code = 500
            json_body = encoder.encode(body)
            payload = {
                'statusCode': status_code,
                'headers': HEADERS,
                'body': json_body
            }
        finally:
            send_to_slack(status_code, json_body)
            log_message = {
                'status_code': status_code,
                'event': event,
                'response': json_body,
            }
            logging.info(log_message, extra={'type': 'request'})
    #     return payload
    # return wrapper
