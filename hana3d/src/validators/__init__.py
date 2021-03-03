"""Upload validation module."""
import logging
from enum import Enum
from typing import Callable, Optional, Tuple

from ..asset.asset_type import AssetType
from ..ui import colors
from ..ui.main import UI
from ..upload.export_data import get_export_data
from ..upload.upload import get_upload_props


class Category(str, Enum):  # noqa : WPS600
    """Category enum class (WARNING | ERROR)."""
    warning = 'WARNING'
    error = 'ERROR'


def dummy_fix_function(asset_type: AssetType, export_data: dict):
    """Fix validation error.

    Parameters:
        asset_type: type of the asset that will be uploaded
        export_data: dict containing objects to be uploaded info

    Does nothing.
    """
    pass  # noqa: WPS420


def dummy_validation_function(asset_type: AssetType, export_data: dict) -> Tuple[bool, str]:
    """Check if validator passes test.

    Parameters:
        asset_type: type of the asset that will be uploaded
        export_data: dict containing objects to be uploaded info

    Returns:
        is_valid, message: whether check passed and a report message
    """
    return True, 'All ok!'


class BaseValidator(object):
    """Base validator class."""

    name: str
    category: Category
    description: str
    validation_result: Tuple[bool, str]
    validation_function: Callable[[AssetType, dict], Tuple[bool, str]]
    fix_function: Callable[[AssetType, dict], None]

    def __init__(  # noqa: WPS211
        self,
        name: str,
        category: Category,
        description: str,
        validation_function: Callable = dummy_validation_function,
        fix_function: Callable = dummy_fix_function,
    ):
        """Check if validator passes test.

        Parameters:
            name: validation name
            category: one of 'WARNING' or 'ERROR'
            description: short description of what is begin checked
            validation_function: function that checks for issues - returns a boolean and a message
            fix_function: function that automatically corrects issues
        """
        self.name = name
        self.category = category
        self.description = description
        self.validation_function = validation_function  # type: ignore
        self.fix_function = fix_function  # type: ignore
        self.validation_result = (False, 'Validation has yet to be run')

    def get_validation_result(self) -> Tuple[bool, str]:
        """Get validation result.

        Returns:
            is_valid, message: whether check passed and a report message
        """
        return self.validation_result

    def run_validation(self, export_data: Optional[dict] = None):
        """Run checks for this validator."""
        props = get_upload_props()
        if not export_data:
            export_data, _ = get_export_data(props)
        asset_type = export_data['type'].lower()
        logging.info(f'Export data: {export_data}')
        self.validation_result = self.validation_function(asset_type, export_data)  # type: ignore

    def run_fix(self, export_data: Optional[dict] = None):
        """Run fix function for this validator."""
        props = get_upload_props()
        if not export_data:
            export_data, _ = get_export_data(props)
        asset_type = export_data['type'].lower()
        logging.info(f'Export data: {export_data}')
        self.fix_function(asset_type, export_data)  # type: ignore
        self.run_validation(export_data)
        if not self.validation_result[0]:
            ui = UI()
            error = f'Could not fix {self.name} automatically'
            ui.add_report(text=error, color=colors.RED)
            logging.error(error)

    def ignore(self):
        """Ignore validator result."""
        self.validation_result = (True, 'Ignored')
