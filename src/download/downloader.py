import logging
import os
import threading

import requests

from .lib import check_existing
from ..async_loop import run_async_function
from ... import paths


class ThreadCom:  # object passed to threads to read background process stdout info
    def __init__(self):
        self.file_size = 1000000000000000  # property that gets written to.
        self.downloaded = 0
        self.lasttext = ''
        self.error = False
        self.report = ''
        self.progress = 0.0
        self.passargs = {}


class Downloader(threading.Thread):
    def __init__(self, asset_data: dict, tcom: ThreadCom):
        super(Downloader, self).__init__()
        self.asset_data = asset_data
        self.tcom = tcom
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

    # def main_download_thread(asset_data, tcom):
    def run(self):
        '''try to download file from hana3d'''
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
            tcom.downloaded = 100
            logging.debug('not downloading, trying to append again')
            return

        file_name = paths.get_download_filenames(asset_data)[0]  # prefer global dir if possible.

        if self.stopped():
            logging.debug(f'stopping download: {asset_data["name"]}')  # noqa WPS204
            return

        tmp_file_name = f'{file_name}_tmp'
        with open(tmp_file_name, 'wb') as tmp_file:
            logging.info(f'Downloading {file_name}')

            response = requests.get(asset_data['download_url'], stream=True)
            total_length = response.headers.get('Content-Length')

            if total_length is None:  # no content length header
                tmp_file.write(response.content)
            else:  # noqa WPS220
                tcom.file_size = int(total_length)
                dl = 0
                for data in response.iter_content(chunk_size=4096):
                    dl += len(data)
                    tcom.downloaded = dl
                    tcom.progress = int(100 * tcom.downloaded / tcom.file_size)
                    tmp_file.write(data)
                    if self.stopped():
                        logging.debug(f'stopping download: {asset_data["name"]}')  # noqa WPS220
                        tmp_file.close()  # noqa : WPS220
                        os.remove(tmp_file_name)  # noqa : WPS220
                        return
        os.rename(tmp_file_name, file_name)
