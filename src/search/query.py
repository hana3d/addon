"""Search Query."""

from datetime import datetime
from typing import Dict

from bpy.types import Context

from ..asset.asset_type import AssetType
from ...config import HANA3D_NAME


class Query(object):  # noqa : WPS230,WPS214
    """Hana3D search query."""

    def __init__(self, context: Context = None, props: Dict = None):
        """Create a Search Query object.

        Args:
            context: Blender context.
            props: Search properties.
        """
        self.context = context

        self.asset_type: AssetType = None
        self.view_id: str = None
        self.job_id: str = None
        self.search_term: str = None
        self.verification_status: str = None
        self.public: bool = False
        self.workspace: str = None
        self.tags: str = None
        self.libraries: str = None

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

        Will return None if context or props were not provided on Query creation.

        Returns:
            datetime: time when the search query was updated
        """
        if not self.context:
            return None

        if f'{HANA3D_NAME}_search_query_updated_at' not in self.context.window_manager:
            return None
        updated_at = self.context.window_manager[f'{HANA3D_NAME}_search_query_updated_at']
        if updated_at is None:
            return None
        return datetime.fromisoformat(updated_at)

    @updated_at.setter
    def updated_at(self, updated_at_value: datetime):
        if updated_at_value is not None and self.context is not None:
            # avoid unnecessary updates because of threads
            updated_at_timeout_s = 20
            if (  # noqa : WPS337
                not self.updated_at
                or (updated_at_value - self.updated_at).total_seconds() > updated_at_timeout_s
            ):
                self.context.window_manager[f'{HANA3D_NAME}_search_query_updated_at'] = updated_at_value.isoformat()  # noqa : E501

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
        self.public = bool(props.public_only)

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
