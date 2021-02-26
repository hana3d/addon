"""Search operator."""

import logging
import os
from typing import Dict, List, Tuple

import bpy
from bpy.props import BoolProperty, IntProperty, StringProperty

from .async_functions import download_thumbnail, search_assets
from .query import Query
from .search import (
    AssetData,
    get_search_props,
    get_search_results,
    load_preview,
    set_original_search_results,
    set_search_results,
)
from ..asset.asset_type import AssetType
from ..async_loop.async_mixin import AsyncModalOperatorMixin
from ..preferences.preferences import Preferences
from ..ui import colors
from ..ui.main import UI
from ... import hana3d_oauth, paths, utils
from ...config import HANA3D_DESCRIPTION, HANA3D_NAME, HANA3D_UI

Thumbnail = Tuple[str, str]


class SearchOperator(AsyncModalOperatorMixin, bpy.types.Operator):  # noqa: WPS214
    """Hana3D search operator."""

    bl_idname = f'view3d.{HANA3D_NAME}_search'
    bl_label = f'{HANA3D_DESCRIPTION} asset search'
    bl_description = 'Search online for assets'
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    own: BoolProperty(  # type: ignore
        name='Own assets only',
        description='Find all own assets',
        default=False,
    )

    author_id: StringProperty(  # type: ignore
        name='Author ID',
        description='Author ID - search only assets by this author',
        default='',
        options={'SKIP_SAVE'},
    )

    get_next: BoolProperty(  # type: ignore
        name='Next page',
        description='Get next page from previous search',
        default=False,
        options={'SKIP_SAVE'},
    )

    keywords: StringProperty(  # type: ignore
        name='Keywords',
        description='Keywords',
        default='',
        options={'SKIP_SAVE'},
    )

    next_index: IntProperty(  # type: ignore
        name='Next index',
        description='Next index to fill with search results',
        default=0,
        options={'SKIP_SAVE'},
    )

    @classmethod
    def poll(cls, context):
        """Search poll.

        Parameters:
            context: Blender context

        Returns:
            bool: only search if no search operation is running
        """
        search_props = get_search_props()
        return not search_props.is_searching

    async def async_execute(self, context):
        """Search async execute.

        Parameters:
            context: Blender context

        Returns:
            enum set in {'RUNNING_MODAL', 'CANCELLED', 'FINISHED'}
        """
        logging.debug('Starting async search')
        search_props = get_search_props()
        if self.author_id != '':
            search_props.search_keywords = ''
        if self.keywords != '':
            search_props.search_keywords = self.keywords

        logging.debug(f'Search_props: {search_props}')
        ui = UI()
        ui_props = getattr(bpy.context.window_manager, HANA3D_UI)
        asset_type = self._get_asset_type_from_ui()

        query = Query(bpy.context, search_props)
        query.asset_type = asset_type
        logging.debug(f'Query object: {query.to_dict()}')

        options = {'get_next': self.get_next}
        logging.debug(f'Search options: {str(options)}')
        ui.add_report(text=f'{HANA3D_DESCRIPTION} searching...', timeout=2)

        if search_props.is_searching:
            return {'FINISHED'}
        search_props.is_searching = True

        try:
            request_data = await search_assets(query, options, ui)
        except Exception:
            return {'CANCELED'}

        tempdir = paths.get_temp_dir(f'{asset_type}_search')

        result_field = []
        ok, error = self._check_errors(request_data)
        if ok:
            run_assetbar_op = getattr(bpy.ops.object, f'{HANA3D_NAME}_run_assetbar_fix_context')
            status = run_assetbar_op()
            logging.debug(f'Asset bar operator status: {status}')

            result_field = self._parse_response(asset_type, request_data)
            logging.debug(f'Parsed results: {len(result_field)}')

            if options['get_next']:
                previous_results = get_search_results(asset_type)
                self.next_index = len(previous_results)
                result_field = previous_results + result_field
                set_search_results(asset_type, result_field)
            else:
                self.next_index = 0
                set_search_results(asset_type, result_field)

            set_original_search_results(asset_type, request_data)

            if len(result_field) < ui_props.scrolloffset:
                ui_props.scrolloffset = 0
            text = f'Found {request_data["count"]} results. '  # noqa #501
            ui.add_report(text=text)
        else:
            logging.error(error)
            ui.add_report(text=error, color=colors.RED)
            search_props.search_error = True

        small_thumbnails, full_thumbnails = self._get_thumbnails(tempdir, request_data)
        await self._load_thumbnails(small_thumbnails, full_thumbnails, asset_type, result_field)

        status = run_assetbar_op()
        logging.debug(f'Asset bar operator status: {status}')

        search_props.is_searching = False
        return {'FINISHED'}

    def _check_errors(self, request_data: Dict) -> Tuple[bool, str]:
        if request_data.get('status_code') == 401:  # noqa: WPS432
            logging.debug(request_data)
            if request_data.get('code') == 'token_expired':
                user_preferences = Preferences().get()
                if user_preferences.api_key != '':
                    hana3d_oauth.refresh_token(immediate=False)
                    return False, request_data.get('description', '')
                return False, 'Missing or wrong api_key in addon preferences'
        elif request_data.get('status_code') == 403:  # noqa: WPS432
            logging.debug(request_data)
            if request_data.get('code') == 'invalid_permissions':
                return False, request_data.get('description', '')
        return True, ''

    def _parse_response(self, asset_type: AssetType, request_data: Dict) -> List[AssetData]:
        result_field = []
        for response in request_data['results']:
            if response['assetType'] != asset_type or not response['files']:
                continue

            download_url, thumbnail, small_thumbnail = self._parse_files(response['files'])

            if not download_url:
                continue

            asset_data = self._create_asset_data(
                thumbnail,
                small_thumbnail,
                download_url,
                response,
            )
            options = utils.params_to_dict(response['parameters'])

            if asset_type == AssetType.model:
                if options.get('boundBoxMinX') is not None:
                    asset_data.bbox_min = (
                        float(options['boundBoxMinX']),
                        float(options['boundBoxMinY']),
                        float(options['boundBoxMinZ']),
                    )
                    asset_data.bbox_max = (
                        float(options['boundBoxMaxX']),
                        float(options['boundBoxMaxY']),
                        float(options['boundBoxMaxZ']),
                    )

            assets_used = bpy.context.window_manager.get(
                f'{HANA3D_NAME}_assets_used', {},
            )
            if asset_data.view_id in assets_used.keys():
                asset_data.downloaded = 100

            result_field.append(asset_data)
        return result_field

    def _parse_files(self, files: List[Dict]) -> Tuple[str, str, str]:
        all_thumbnails: List[str] = []
        for rfile in files:
            if rfile['fileType'] == 'thumbnail':
                thumbnail_name = paths.extract_filename_from_url(
                    rfile['fileThumbnailLarge'],
                )
                small_thumbnail_name = paths.extract_filename_from_url(
                    rfile['fileThumbnail'],
                )
                all_thumbnails.append(thumbnail_name)

            if rfile['fileType'] == 'blend':
                download_url = rfile['downloadUrl']
        return download_url, thumbnail_name, small_thumbnail_name

    def _create_asset_data(
        self,
        thumbnail_name: str,
        small_thumbnail_name: str,
        download_url: str,
        response: Dict,
    ) -> AssetData:
        # Check for assetBaseId for backwards compatibility
        view_id = response.get('viewId') or response.get('assetBaseId') or ''
        tooltip = utils.generate_tooltip(
            response['name'],
            response['description'],
        )
        asset_data = AssetData(
            thumbnail_name,
            small_thumbnail_name,
            download_url,
            response['id'],
            view_id,
            response['name'],
            response['assetType'],
            tooltip,
            response['tags'],
            response['verificationStatus'],
            str(response['author']['id']),
            response['description'] or '',
            response.get('render_jobs', []),
            response.get('workspace', ''),
        )

        asset_data.created = str(response.get('created'))
        asset_data.revision = str(response.get('revision'))

        if 'metadata' in response and response['metadata'] is not None:
            asset_data.metadata = response['metadata']
        if 'libraries' in response and response['libraries'] is not None:
            asset_data.libraries = response['libraries']
        return asset_data

    def _get_thumbnails(
        self,
        tempdir: str,
        request_data: Dict,
    ) -> Tuple[List[Thumbnail], List[Thumbnail]]:
        thumb_small_urls: List = []
        thumb_small_filepaths: List = []
        thumb_full_urls: List = []
        thumb_full_filepaths: List = []
        # END OF PARSING
        for rdata in request_data.get('results', []):
            for rfile in rdata['files']:
                # TODO move validation of published assets to server, too many checks here.
                thumbnail = rfile['fileThumbnailLarge']
                small_thumbnail = rfile['fileThumbnail']
                if rfile['fileType'] != 'thumbnail':
                    continue

                if small_thumbnail is None:
                    thumb_small_urls.append(None)
                    thumb_small_filepaths.append(None)
                else:
                    thumb_small_urls.append(small_thumbnail)
                    imgname = paths.extract_filename_from_url(small_thumbnail)
                    imgpath = os.path.join(tempdir, imgname)
                    thumb_small_filepaths.append(imgpath)

                if thumbnail is None:
                    thumb_full_urls.append(None)
                    thumb_full_filepaths.append(None)
                else:
                    thumb_full_urls.append(thumbnail)
                    imgname = paths.extract_filename_from_url(rfile['fileThumbnailLarge'])
                    imgpath = os.path.join(tempdir, imgname)
                    thumb_full_filepaths.append(imgpath)

        small_thumbnails = zip(thumb_small_filepaths, thumb_small_urls)
        full_thumbnails = zip(thumb_full_filepaths, thumb_full_urls)

        return list(small_thumbnails), list(full_thumbnails)

    def _get_asset_type_from_ui(self) -> AssetType:
        uiprops = getattr(bpy.context.window_manager, HANA3D_UI)
        return uiprops.asset_type_search.lower()

    async def _load_thumbnails(
        self,
        small_thumbnails: List[Tuple],
        large_thumbnails: List[Tuple],
        asset_type: AssetType,
        result_field: List[AssetData],
    ):
        for small, large in zip(small_thumbnails, large_thumbnails):
            imgpath, url = small
            imgpath_large, url_large = large
            if imgpath is not None and not os.path.exists(imgpath):
                await download_thumbnail(imgpath, url)
            if imgpath_large is not None and not os.path.exists(imgpath_large):
                await download_thumbnail(imgpath_large, url_large)
            current_asset_type = self._get_asset_type_from_ui()
            if current_asset_type == asset_type:
                load_preview(asset_type, result_field[self.next_index], self.next_index)
            self.next_index += 1



classes = (
    SearchOperator,
)


def register():
    """Search register."""
    for class_ in classes:
        bpy.utils.register_class(class_)


def unregister():
    """Search unregister."""
    for class_ in reversed(classes):
        bpy.utils.unregister_class(class_)
