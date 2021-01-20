"""External dependencies loader."""

import glob
import logging
import os
import sys

my_dir = os.path.join(os.path.dirname(__file__))
log = logging.getLogger(__name__)


def load_wheel(module_name, fname_prefix):
    """Load a wheel from 'fname_prefix*.whl', unless the named module can be imported.

    This allows us to use system-installed packages before falling back to the shipped wheels.
    This is useful for development, less so for deployment.

    Arguments:
        module_name: str,
        fname_prefix: str,
    """
    try:
        module = __import__(module_name)    # noqa: WPS421
    except ImportError as ex:
        log.debug(f'Unable to import {module_name} directly, will try wheel: {ex}')
    else:
        log.debug(
            f'Loaded {module_name} from {module.__file__}, \
            no need to load wheel {fname_prefix}',  # noqa: WPS609
        )
        return

    sys.path.append(wheel_filename(fname_prefix))
    module = __import__(module_name)    # noqa: WPS421
    log.debug(f'Loaded {module_name} from {module.__file__}')    # noqa: WPS609


def wheel_filename(fname_prefix: str) -> str:
    """Find wheel file name from a name prefix.

    Arguments:
        fname_prefix: str

    Returns:
        str: latest matching wheel name

    Exception:
        RuntimeError: Unable to find wheel
    """
    path_pattern = os.path.join(my_dir, f'{fname_prefix}*.whl')
    wheels = glob.glob(path_pattern)
    if not wheels:
        raise RuntimeError(f'Unable to find wheel at {path_pattern}')

    # If there are multiple wheels that match, load the latest one.
    wheels.sort()
    return wheels[-1]


def load_wheels():
    """Load required wheels."""
    load_wheel('bugsnag', 'bugsnag')
    load_wheel('sentry_sdk', 'sentry_sdk')
