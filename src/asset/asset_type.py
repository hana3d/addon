"""Asset Type."""

from enum import Enum


class AssetType(str, Enum):  # noqa : WPS600
    """Asset Type enum class (model | material | scene)."""

    model = 'model'
    material = 'material'
    scene = 'scene'
