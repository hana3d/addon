"""Search Query."""

from typing import Dict
from ..asset.asset_type import AssetType
from datetime import date, datetime

from bpy.types import Context

from ...config import HANA3D_NAME


class Query(object):
    """Hana3D search query."""

    asset_type: AssetType = None
    view_id: str = None
    job_id: str = None
    search_term: str = None
    verification_status: str = None
    public: bool = False
    workspace: str = None
    tags: str = None
    libraries: str = None

    def __init__(self, context: Context = None, props: Dict = None):
        """Create a Search Query object.

        Args:
            context: Blender context.
        """
        self.context = context

        if props is not None:
            self.updated_at = datetime.now()
            self._add_view_id_search_term(props)
            self._add_verification_status(props)
            self._add_public(props)
            self._add_workspace(props)
            self._add_tags(props)
            self._add_libraries(props)

    @property
    def updated_at(self) -> datetime:
        """Get the datetime when the search query was updated.

        Returns:
            datetime: time when the search query was updated if context was provided
        """
        if not self.context:
            return None

        updated_at = self.context.window_manager[f'{HANA3D_NAME}_search_query_updated_at']
        if updated_at is not None:
            return datetime.fromisoformat(updated_at)
        else:
            return None

    @updated_at.setter
    def updated_at(self, updated_at_value: datetime):
        if updated_at_value is not None and self.context is not None:
            self.context.window_manager[f'{HANA3D_NAME}_search_query_updated_at'] = updated_at_value.isoformat(
            )

    def _add_view_id_search_term(self, props: Dict):
        keywords = props.search_keywords
        if keywords != '':
            if keywords.startswith('view_id:'):
                self.view_id = keywords.replace('view_id:', '')
            else:
                self.search_term = keywords

    def _add_verification_status(self, props: Dict):
        if props.search_verification_status != 'ALL':
            self.verification_status = props.search_verification_status.lower()

    def _add_public(self, props: Dict):
        if props.public_only:
            self.public = True

    def _add_workspace(self, props: Dict):
        if props.workspace != '' and not props.public_only:
            self.workspace = props.workspace

    def _add_tags(self, props: Dict):
        tags = []
        for tag in props.tags_list.keys():
            if props.tags_list[tag].selected is True:
                tags.append(tag)
        self.tags = ','.join(tags)

    def _add_libraries(self, props: Dict):
        libraries = []
        for library in props.libraries_list.keys():
            if props.libraries_list[library].selected is True:
                libraries.append(props.libraries_list[library].id_)
        self.libraries = ','.join(libraries)
