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

import os
import threading
from typing import List

import requests

from . import paths, rerequests
from .src.search.query import Query


def download_file(file_path: str, url: str) -> str:
    response = requests.get(url, stream=True)

    # Write to temp file and then rename to avoid reading errors as file is being downloaded
    tmp_file = file_path + '_tmp'
    with open(tmp_file, 'wb') as f:
        f.write(response.content)
    os.rename(tmp_file, file_path)


def get_render_jobs(asset_type: str, view_id: str, job_id: str = None) -> List[dict]:
    query = {}
    query['view_id'] = view_id
    if job_id:
        query['job_id'] = job_id
    url = paths.get_api_url('renders', query=query)
    response = rerequests.get(url, headers=rerequests.get_headers())
    assert response.ok, response.text

    jobs = response.json()
    download_dir = paths.get_download_dirs(asset_type)[0]

    for job in jobs:
        url = job['file_url']

        filename = paths.extract_filename_from_url(url)
        file_path = os.path.join(download_dir, filename)
        job['file_path'] = file_path

        if not os.path.exists(file_path):
            thread = threading.Thread(
                target=download_file,
                args=(job['file_path'], job['file_url']),
                daemon=True,
            )
            thread.start()

    return jobs
