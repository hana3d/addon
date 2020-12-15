"""Singleton metaclass."""
from typing import Dict, Type


# See https://stackoverflow.com/questions/6760685/creating-a-singleton-in-python
# for more context in how to implement a singleton in Python
class Singleton(type):
    """Singleton metaclass."""

    # See https://www.python.org/dev/peps/pep-0484/#the-problem-of-forward-declarations
    _instances: Dict[Type['Singleton'], Type[object]] = {}

    def __call__(cls, *args, **kwargs):  # noqa: D102
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]
