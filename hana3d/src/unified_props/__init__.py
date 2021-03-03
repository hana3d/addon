"""Unified Properties."""
from bpy.types import Context

from ...config import HANA3D_NAME


class Unified(object):
    """Hana3D global information."""

    def __init__(self, context: Context):
        """Create a Unified object.

        Args:
            context: Blender context.
        """
        self.context = context

    @property
    def props(self):
        """Get unified props.

        Returns:
            Any | None: unified props if available
        """
        return getattr(self.context.window_manager, HANA3D_NAME)
