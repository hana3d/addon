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
import logging
import os
import threading
from typing import List

import requests

from . import paths, render, rerequests


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


def update_render_list(
    props,
    jobs: dict = None,
    set_jobs: bool = True,
):
    """Update render list on UI.

    Parameters:
        props: upload props
        jobs: dict
        set_jobs: True if jobs exists, False otherwise
    """
    if not hasattr(props, 'view_id'):  # noqa WPS421
        return
    preview_collection = render.render_previews[props.view_id]
    if not hasattr(preview_collection, 'previews'):  # noqa WPS421
        preview_collection.previews = []

    if set_jobs:
        jobs = props.render_data['jobs']
    else:
        jobs = get_render_jobs(props.asset_type, props.view_id)
        props.render_data['jobs'] = jobs

    if jobs is not None:
        update_props_render_list(props, jobs, preview_collection)

        logging.debug(f'Updated renders for {props.name}')


def update_props_render_list(props, jobs, preview_collection):  # noqa WPS210
    """Update render list on props.

    Parameters:
        props: Upload props
        jobs: not None
        preview_collection: List[Tuple] not None
    """
    props.render_list.clear()
    available_previews = []
    sorted_jobs = sorted(jobs, key=lambda jb: jb['created'])
    for index, job in enumerate(sorted_jobs):
        job_id = job['id']
        if job_id not in preview_collection:
            preview_img = preview_collection.load(job_id, job['file_path'], 'IMAGE')
        else:
            preview_img = preview_collection[job_id]

        new_render = props.render_list.add()
        new_render['name'] = job['job_name'] or ''
        new_render['index'] = index
        new_render['job_id'] = job_id
        new_render['icon_id'] = preview_img.icon_id
        new_render['file_path'] = job['file_path']
        enum_item = (job_id, job['job_name'] or '', '', preview_img.icon_id, index)
        available_previews.append(enum_item)
    preview_collection.previews = available_previews
