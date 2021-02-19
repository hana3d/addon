"""Upload validation module."""
from enum import Enum
from typing import Callable, Tuple


class Category(str, Enum):  # noqa : WPS600
    """Category enum class (WARNING | ERROR)."""

    warning = 'WARNING'
    error = 'ERROR'

def dummy_fix_function():
    pass

def dummy_validation_function():
    return True, 'All ok!'

class BaseValidator():
    name: str
    category: Category
    description: str
    validation_result: Tuple[bool, str]
    validation_function: Callable[..., Tuple[bool, str]]
    fix_function: Callable

    def __init__(
        self,
        name: str,
        category: Category,
        description: str,
        validation_function: Callable = dummy_validation_function,
        fix_function: Callable = dummy_fix_function
        ):
        self.name = name
        self.category = category
        self.description = description
        setattr(self, "validation_function", validation_function)
        setattr(self, "fix_function", fix_function)
        self.validation_result = (False, 'Validation has yet to be run')

    def get_validation_result(self) -> Tuple[bool , str]:
        return self.validation_result

    def run_validation(self):
        self.validation_result = self.validation_function()
    
    def run_fix(self):
        self.fix_function()
        self.run_validation()
        assert self.validation_result[0], 'Could not fix the problem automatically'

    def ignore(self):
        self.validation_result = (True, 'Ignored')
