import asyncio
import logging
import os
import threading

import requests

from .lib import check_existing
from ..async_loop import run_async_function
from ... import paths

class ThreadCom(object):  # object passed to threads to read background process stdout info
    def __init__(self):
        self.error = False
        self.report = ''
        self.passargs = {}


class Downloader(object):
    def __init__(self, asset_data: dict, tcom: ThreadCom):
        self.asset_data = asset_data
        self.tcom = tcom
        self._task = None
        self._queue = asyncio.LifoQueue()
        self._progress = 0

        self._stop_event = threading.Event()
        self._remove_event = threading.Event()
        self._finish_event = threading.Event()

    def stop(self):
        self._stop_event.set()

    def stopped(self):
        return self._stop_event.is_set()

    def mark_remove(self):
        self._remove_event.set()

    @property
    def marked_remove(self):
        return self._remove_event.is_set()

    def finish(self):
        self._finish_event.set()

    @property
    def finished(self):
        return self._finish_event.is_set()

    def is_alive(self):
        return not self._task.done() if self._task else False

    def progress(self):
        try:
            self._progress = max(self._queue.get_nowait(), self._progress)
        except Exception:
            logging.debug('No new messages in the queue')
        return self._progress


    def start(self):
        """try to download file from hana3d"""
        asset_data = self.asset_data
        tcom = self.tcom

        if tcom.error:
            return

        # only now we can check if the file already exists.
        # This should have 2 levels, for materials
        # different than for the non free content.
        # delete is here when called after failed append tries.
        if check_existing(asset_data) and not tcom.passargs.get('delete'):
            # this sends the thread for processing,
            # where another check should occur,
            # since the file might be corrupted.
            self._progress = 100
            logging.debug('not downloading, trying to append again')
            return

        if self.stopped():
            logging.debug(f'stopping download: {asset_data["name"]}')  # noqa WPS204
            return

        self._task = run_async_function(self._download_async)


    async def _download_async(self):
        asset_data = self.asset_data

        file_name = paths.get_download_filenames(asset_data)[0]  # prefer global dir if possible.

        tmp_file_name = f'{file_name}_tmp'
        with open(tmp_file_name, 'wb') as tmp_file:
            logging.info(f'Downloading {file_name}')

            response = requests.get(asset_data['download_url'], stream=True)
            total_length = response.headers.get('Content-Length')

            if total_length is None:  # no content length header
                tmp_file.write(response.content)
                return

            file_size = int(total_length)
            downloaded = 0
            for data in response.iter_content(chunk_size=4096):
                downloaded += len(data)
                progress = int(100 * downloaded / file_size)
                await self._queue.put(progress)
                tmp_file.write(data)
                if self.stopped():
                    logging.debug(f'stopping download: {asset_data["name"]}')
                    tmp_file.close()
                    os.remove(tmp_file_name)
                    return
        os.rename(tmp_file_name, file_name)
