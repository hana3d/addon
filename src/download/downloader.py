"""Downloader class."""
import asyncio
import logging
import os
import threading

import requests

from .lib import check_existing
from ..async_loop import run_async_function
from ... import paths


class Downloader(object):  # noqa: WPS214
    """Class responsible for downloading assets asynchronously."""

    def __init__(self, asset_data: dict, **passargs):
        """Create a Downloader object.

        Parameters:
            asset_data: Asset Data
            passargs: Keyword arguments
        """
        self.asset_data = asset_data
        self.passargs = passargs

        self.finished = False

        self._task = None
        self._queue = asyncio.LifoQueue()
        self._progress = 0
        self._stop_event = threading.Event()

    def stop(self) -> None:
        """Stop current download."""
        self._stop_event.set()

    def stopped(self) -> bool:
        """Return if the download should be (or has been) stopped.

        Returns:
            bool: True if the current download should stop or will stop, False otherwise
        """
        return self._stop_event.is_set()

    def is_alive(self) -> bool:
        """Return if the download is currently happening.

        Returns:
            bool: True if the download has started and not finished, False otherwise
        """
        return not self._task.done() if self._task else False

    def set_progress(self, progress: int) -> None:
        """Manually updates the download progress.

        Parameters:
            progress: value to which the progress should be set
        """
        self._progress = progress

    def progress(self) -> int:
        """Lazily updates the download progress and returns it.

        Returns:
            int: progress of the download
        """
        try:
            self._progress = max(self._queue.get_nowait(), self._progress)
        except Exception:  # noqa: S110
            pass  # noqa: WPS420
        return self._progress

    def start(self):
        """Try to download file from Hana3D."""
        asset_data = self.asset_data

        # only now we can check if the file already exists.
        # This should have 2 levels, for materials
        # different than for the non free content.
        # delete is here when called after failed append tries.
        if check_existing(asset_data) and not self.passargs.get('delete'):
            # this sends the thread for processing,
            # where another check should occur,
            # since the file might be corrupted.
            self._progress = 100
            logging.debug('Not downloading, trying to append again')
            return

        if self.stopped():
            logging.debug(f'Stopping download: {asset_data["name"]}')  # noqa WPS204
            return

        self._task = run_async_function(self._download_async)

    def _read_chunk(self, iterator):
        try:
            return next(iterator)
        except Exception:
            return b''

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
            iterator = response.iter_content(chunk_size=4096)  # noqa: WPS432
            loop = asyncio.get_event_loop()
            while True:
                # TODO: try to use thread pool for speeding this up?
                download_data = await loop.run_in_executor(None, self._read_chunk, iterator)
                if not download_data:
                    break
                downloaded += len(download_data)
                progress = int(100 * downloaded / file_size)
                await self._queue.put(progress)
                tmp_file.write(download_data)
                if self.stopped():
                    logging.debug(f'Stopping download: {asset_data["name"]}')
                    tmp_file.close()
                    os.remove(tmp_file_name)
                    return
        os.rename(tmp_file_name, file_name)
