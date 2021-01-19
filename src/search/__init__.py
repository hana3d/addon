"""Search assets module."""

import json
import logging
import os
from typing import Dict, List, Tuple

import bpy
from bpy.props import BoolProperty, StringProperty

from .asset_search import AssetSearch
from .async_functions import download_thumbnail, search_assets
from .query import Query
from .search import check_errors, load_previews
from ..asset.asset_type import AssetType
from ..async_loop.async_mixin import AsyncModalOperatorMixin
from ..ui.main import UI
from ... import paths, utils
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
    query: Dict[AssetType, Query] = {}
    results: Dict[AssetType, AssetSearch] = {}

    own: BoolProperty(  # type: ignore
        name='Own assets only',
        description='Find all own assets',
        default=False
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
        name='Is searching',
        description='True if assets are being searched',
        default=False,
        options={'SKIP_SAVE'},
    )

    search_error: BoolProperty(  # type: ignore
        name='Search error',
        description='True if there was an error in search',
        default=False,
        options={'SKIP_SAVE'},
    )

    keywords: StringProperty(  # type: ignore
        name='Keywords',
        description='Keywords',
        default='',
        options={'SKIP_SAVE'},
    )

    def get_query(self, asset_type: AssetType) -> Query:
        """Get current query by asset type.

        Returns:
            Query: query by asset type.
        """
        return self.queries[asset_type]

    def set_query(self, asset_type: AssetType, query: Query):
        self.queries[asset_type] = query

    def get_results(self, asset_type: AssetType) -> AssetSearch:
        """Get current search results by asset type.

        Returns:
            Query: query by asset type.
        """
        return self.results[asset_type]

    def set_results(self, asset_type: AssetType, results: AssetSearch):
        self.results[asset_type] = results


    @classmethod
    def poll(cls, context):
        return not self.is_searching

    async def async_execute(self, context):
        """Search async execute.

        Parameters:
            context: Blender context

        Returns:
            enum set in {‘RUNNING_MODAL’, ‘CANCELLED’, ‘FINISHED’}
        """

        search_props = self.props
        if self.author_id != '':
            search_props.search_keywords = ''
        if self.keywords != '':
            search_props.search_keywords = self.keywords

        ui = UI()
        ui_props = getattr(bpy.context.window_manager, HANA3D_UI)
        search_props.asset_type = ui_props.asset_type.lower()
        query = Query(bpy.context, search_props)

        if self.is_searching and self.get_next:
            return

        self.is_searching = True

        params = {'get_next': self.get_next}
        ui.add_report(text=f'{HANA3D_DESCRIPTION} searching...', timeout=2)

        request_data = await search_assets(query, params, ui)
        #search_results = parse(request_data)

        tempdir = paths.get_temp_dir(f'{query.asset_type}_search')
        asset_type = search_props.asset_type
        asset_search = AssetSearch(bpy.context, asset_type)
        asset_search.results = []  # noqa : WPS110

        result_field = []
        ok, error = check_errors(request_data)
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

            asset_search.results = result_field  # noqa : WPS110
            asset_search.results_original = request_data
            self.set_results(search_props.asset_type, asset_search)

            load_previews(asset_type, asset_search)

            ui_props = getattr(bpy.context.window_manager, HANA3D_UI)
            if len(result_field) < ui_props.scrolloffset:
                ui_props.scrolloffset = 0
            self.is_searching = False
            self.search_error = False
            text = f'Found {search_object.results_original["count"]} results. '  # noqa #501
            ui.add_report(text=text)

        else:
            logging.error(error)
            ui = UI()
            ui.add_report(text=error, color=colors.RED)
            props.search_error = True

        mt('preview loading finished')

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


    def _get_thumbnails(tempdir: str, request_data: Dict) -> Tuple:
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

    async def _download_thumbnails(thumbnails: List[Tuple]):
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

