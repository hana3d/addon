import asyncio
import requests
import functools

import bpy

from . import async_loop
from ..paths import get_api_url
from .. import hana3d_oauth, rerequests


async def do_request():
    partial = functools.partial(requests.get, 'https://api.hana3d.com')
    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(None, partial)
    print(response)


async def test_request():
    task1 = asyncio.create_task(do_request())
    await task1
    # loop = asyncio.get_event_loop()
    # loop.run_until_complete(do_request())


class TestRequest(async_loop.AsyncModalOperatorMixin, bpy.types.Operator):
    bl_idname = 'test.request'
    bl_label = 'Runs the asyncio request'

    async def async_execute(self, context):
        # asyncio.run(test_request())
        # loop = asyncio.get_event_loop()
        # loop.run_until_complete(do_request())
        await do_request()

        self._state = 'QUIT'


def register():
    bpy.utils.register_class(TestRequest)


def unregister():
    bpy.utils.unregister_class(TestRequest)
