"""Search Query."""
from typing import Dict

from bpy.types import Context

from ..asset.asset_type import AssetType
from ...config import HANA3D_NAME


class Query(object):  # noqa : WPS230,WPS214
    """Hana3D search query."""

    def __init__(self, context: Context = None, search_props: Dict = None):
        """Create a Search Query object.

        Args:
            context: Blender context.
            search_props: Search properties.
        """
        self.context = context

        self.asset_type: AssetType = None
        self.view_id: str = ''
        self.job_id: str = ''
        self.search_term: str = ''
        self.verification_status: str = ''
        self.public: bool = False
        self.workspace: str = ''
        self.tags: str = ''
        self.libraries: str = ''
        self.results_per_page = 100

        if search_props is not None:
            self._add_view_id_search_term(search_props)
            self._add_verification_status(search_props)
            self._add_public(search_props)
            self._add_workspace(search_props)
            self._add_tags(search_props)
            self._add_libraries(search_props)

    def _add_view_id_search_term(self, search_props: Dict):
        keywords = search_props.search_keywords
        if keywords != '':
            if keywords.startswith('view_id:'):
                self.view_id = keywords.replace('view_id:', '')
            else:
                self.search_term = keywords

    def _add_verification_status(self, search_props: Dict):
        if search_props.search_verification_status != 'ALL':
            self.verification_status = search_props.search_verification_status.lower()

    def _add_public(self, search_props: Dict):
        self.public = bool(search_props.public_only)

    def _add_workspace(self, search_props: Dict):
        unified_props = getattr(self.context.window_manager, HANA3D_NAME)
        if unified_props.workspace != '' and not search_props.public_only:
            self.workspace = unified_props.workspace

    def _add_tags(self, search_props: Dict):
        tags = []
        for tag in search_props.tags_list.keys():
            if search_props.tags_list[tag].selected is True:
                tags.append(tag)
        self.tags = ','.join(tags)

    def _add_libraries(self, search_props: Dict):
        libraries = []
        for library in search_props.libraries_list.keys():
            if search_props.libraries_list[library].selected is True:
                libraries.append(search_props.libraries_list[library].id_)
        self.libraries = ','.join(libraries)

    def save_last_query(self):
        """Save last search query to the Blender context."""
        self.context.window_manager[f'{HANA3D_NAME}_last_query'] = str(vars(self))  # noqa : WPS421

    def get_last_query(self) -> str:
        """Get last search query from the Blender context.

        Returns:
            str: the last search query, stringified
        """
        return self.context.window_manager.get(f'{HANA3D_NAME}_last_query', '')

    def to_dict(self) -> Dict:
        """Get the search query as a Dict.

        Returns:
            Dict: the query string as a dictionary
        """
        return vars(self)   # noqa: WPS421
