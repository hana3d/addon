"""Search assets module."""

import json
import logging
import os
from typing import Dict, List, Tuple

import bpy
from bpy.props import BoolProperty, StringProperty

from . import search
from .async_functions import download_thumbnail, search_assets
from .query import Query
from ..asset.asset_type import AssetType
from ..async_loop.async_mixin import AsyncModalOperatorMixin
from ..ui.main import UI
from ... import hana3d_oauth, paths, utils
from ...config import HANA3D_DESCRIPTION, HANA3D_NAME, HANA3D_UI

asset_types = (
    ('MODEL', 'Model', 'set of objects'),
    ('SCENE', 'Scene', 'scene'),
    ('MATERIAL', 'Material', 'any .blend Material'),
    ('ADDON', 'Addon', 'addon'),
)


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

    is_searching: BoolProperty(  # type: ignore
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

    @classmethod
    def poll(cls, context):
        """Search poll.

        Parameters:
            context: Blender context

        Returns:
            bool: can always search
        """
        return True

    async def async_execute(self, context):
        """Search async execute.

        Parameters:
            context: Blender context

        Returns:
            enum set in {‘RUNNING_MODAL’, ‘CANCELLED’, ‘FINISHED’}
        """
        logging.debug('STARTING ASYNC SEARCH')
        search_props = search.get_search_props()
        if self.author_id != '':
            search_props['search_keywords'] = ''
        if self.keywords != '':
            search_props['search_keywords'] = self.keywords

        logging.debug(f'GOT SEARCH_PROPS: {search_props}')
        ui = UI()
        ui_props = getattr(bpy.context.window_manager, HANA3D_UI)
        asset_type = ui_props.asset_type.lower()

        search_props['asset_type'] = asset_type

        logging.debug('CREATING QUERY OBJECT')
        query = Query(bpy.context, search_props)
        logging.debug(f'GOT QUERY OBJECT: {query.to_dict()}')

        if search_props.get('is_searching') and self.get_next:
            return

        search_props['is_searching'] = True

        params = {'get_next': self.get_next}
        ui.add_report(text=f'{HANA3D_DESCRIPTION} searching...', timeout=2)

        request_data = await search_assets(query, params, ui)

        tempdir = paths.get_temp_dir(f'{query.asset_type}_search')

        result_field = []
        ok, error = self._check_errors(request_data)
        if ok:
            run_assetbar_op = getattr(bpy.ops.object, f'{HANA3D_NAME}_run_assetbar_fix_context')
            run_assetbar_op()
            for r in request_data['results']:
                if r['assetType'] == asset_type:
                    if len(r['files']) > 0:
                        tname = None
                        allthumbs = []
                        durl, tname = None, None
                        for f in r['files']:
                            if f['fileType'] == 'thumbnail':
                                tname = paths.extract_filename_from_url(f['fileThumbnailLarge'])
                                small_tname = paths.extract_filename_from_url(
                                    f['fileThumbnail'],
                                )
                                allthumbs.append(tname)

                            tdict = {}
                            for i, t in enumerate(allthumbs):
                                tdict['thumbnail_%i'] = t
                            if f['fileType'] == 'blend':
                                durl = f['downloadUrl']
                        if durl:    # noqa: WPS220
                            # Check for assetBaseId for backwards compatibility
                            view_id = r.get('viewId') or r.get('assetBaseId') or ''
                            tooltip = utils.generate_tooltip(
                                r['name'],
                                r['description'],
                            )
                            asset_data = {
                                'thumbnail': tname,
                                'thumbnail_small': small_tname,
                                'download_url': durl,
                                'id': r['id'],
                                'view_id': view_id,
                                'name': r['name'],
                                'asset_type': r['assetType'],
                                'tooltip': tooltip,
                                'tags': r['tags'],
                                'verification_status': r['verificationStatus'],
                                'author_id': str(r['author']['id']),
                                'description': r['description'] or '',
                                'render_jobs': r.get('render_jobs', []),
                                'workspace': r.get('workspace', ''),
                            }
                            asset_data['downloaded'] = 0

                            if 'metadata' in r and r['metadata'] is not None:
                                asset_data['metadata'] = r['metadata']
                            if 'created' in r and r['created'] is not None:
                                asset_data['created'] = r['created']
                            if 'libraries' in r and r['libraries'] is not None:
                                asset_data['libraries'] = r['libraries']

                            params = utils.params_to_dict(r['parameters'])

                            if asset_type == 'model':
                                if params.get('boundBoxMinX') is not None:
                                    bbox = {
                                        'bbox_min': (
                                            float(params['boundBoxMinX']),
                                            float(params['boundBoxMinY']),
                                            float(params['boundBoxMinZ']),
                                        ),
                                        'bbox_max': (
                                            float(params['boundBoxMaxX']),
                                            float(params['boundBoxMaxY']),
                                            float(params['boundBoxMaxZ']),
                                        ),
                                    }

                                else:
                                    bbox = {
                                        'bbox_min': (-0.5, -0.5, 0),
                                        'bbox_max': (0.5, 0.5, 1),
                                    }
                                asset_data.update(bbox)

                            asset_data.update(tdict)
                            assets_used = bpy.context.window_manager.get(  # noqa : WPS220
                                f'{HANA3D_NAME}_assets_used', {},
                            )
                            if view_id in assets_used.keys():  # noqa : WPS220
                                asset_data['downloaded'] = 100  # noqa : WPS220

                            result_field.append(asset_data)  # noqa : WPS220

            search.set_results(asset_type, result_field)
            search.set_original_results(asset_type, request_data)
            search.load_previews(asset_type, result_field)

            if len(result_field) < ui_props.scrolloffset:
                ui_props.scrolloffset = 0
            self.is_searching = False
            text = f'Found {search_object.results_original["count"]} results. '  # noqa #501
            ui.add_report(text=text)

        else:
            logging.error(error)
            ui = UI()
            ui.add_report(text=error, color=colors.RED)
            #se.search_error = True

        #mt('preview loading finished')

        #search_assets(query, params, props, ui)

        # we save here because a missing thumbnail check is in the previous loop
        # we can also prepend previous results. These have downloaded thumbnails already...
        if params['get_next']:
            request_data['results'][0:0] = origdata['results']

        json_filepath = os.path.join(tempdir, f'{asset_type}_searchresult.json')
        with open(json_filepath, 'w') as outfile:
            json.dump(request_data, outfile)

        small_thumbnails, full_thumbnails = _get_thumbnails(tempdir, request_data)
        await _download_thumbnails(small_thumbnails)

        return {'FINISHED'}

    def _check_errors(self, request_data: Dict) -> Tuple[bool, str]:
        if request_data.get('status_code') == 401:
            logging.debug(request_data)
            if request_data.get('code') == 'token_expired':
                user_preferences = bpy.context.preferences.addons[HANA3D_NAME].preferences
                if user_preferences.api_key != '':
                    hana3d_oauth.refresh_token(immediate=False)
                    return False, request_data.get('description', '')
                return False, 'Missing or wrong api_key in addon preferences'
        elif request_data.get('status_code') == 403:
            logging.debug(request_data)
            if request_data.get('code') == 'invalid_permissions':
                return False, request_data.get('description', '')
        return True, ''

    def _get_thumbnails(self, tempdir: str, request_data: Dict) -> Tuple:
        thumb_small_urls = []
        thumb_small_filepaths = []
        thumb_full_urls = []
        thumb_full_filepaths = []
        # END OF PARSING
        for d in request_data.get('results', []):
            for f in d['files']:
                # TODO move validation of published assets to server, too many checks here.
                if (
                    f['fileType'] == 'thumbnail'
                    and f['fileThumbnail'] is not None
                    and f['fileThumbnailLarge'] is not None
                ):
                    if f['fileThumbnail'] is None:
                        f['fileThumbnail'] = 'NONE'
                    if f['fileThumbnailLarge'] is None:
                        f['fileThumbnailLarge'] = 'NONE'

                    thumb_small_urls.append(f['fileThumbnail'])
                    thumb_full_urls.append(f['fileThumbnailLarge'])

                    imgname = paths.extract_filename_from_url(f['fileThumbnail'])
                    imgpath = os.path.join(tempdir, imgname)
                    thumb_small_filepaths.append(imgpath)

                    imgname = paths.extract_filename_from_url(f['fileThumbnailLarge'])
                    imgpath = os.path.join(tempdir, imgname)
                    thumb_full_filepaths.append(imgpath)

        small_thumbnails = zip(thumb_small_filepaths, thumb_small_urls)
        full_thumbnails = zip(thumb_full_filepaths, thumb_full_urls)

        return small_thumbnails, full_thumbnails

    def _get_asset_type_from_ui(self) -> AssetType:
        uiprops = getattr(self.context.window_manager, HANA3D_UI)
        return uiprops.asset_type.lower()

    async def _download_thumbnails(self, thumbnails: List[Tuple]):
        for imgpath, url in thumbnails:
            if os.path.exists(imgpath):
                await download_thumbnail(imgpath, url)


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
