"""Search."""

from dataclasses import dataclass

from ...config import HANA3D_NAME


class Search(object):
    """Hana3D search information."""

    def __init__(self, context):
        """Create a Search object."""
        self.context = context

    def results(self):
        """Get search results.

        Returns:
            SearchResult[]: search results
        """
        if f'{HANA3D_NAME}_search_results' not in self.context.window_manager:
            return []
        return self.context.window_manager[f'{HANA3D_NAME}_search_results']


@dataclass
class SearchResult(object):
    """Hana3D search result."""

    x: str
