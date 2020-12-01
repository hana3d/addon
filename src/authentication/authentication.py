"""Hana3D authentication using Auth0."""

import time

from ...hana3d_oauth import refresh_token
from ..preferences.preferences import Preferences
from ..preferences.profile import Profile
from ..async_loop import run_async_function


class Authentication(object):
    """Hana3D authentication."""

    def __init__(self):
        """Create an Authentication object."""
        self.preferences = Preferences()
        self.profile = Profile()

    def refresh_token_timer(self) -> str:
        """Refresh the API key token.

        Returns:
            str: api_key_life
        """
        print('refresh_token_timer')  # noqa: WPS421
        self.update_tokens()
        return self.preferences.get().api_key_life

    def update_tokens(self) -> None:
        """Refresh the API key token."""
        api_key_exists = self.preferences.get().api_key
        api_key_has_timed_out = self.preferences.get().api_key_timeout < time.time()
        if (api_key_exists and api_key_has_timed_out):
            refresh_token(immediate=False)
        if api_key_exists and self.profile.get() is None:
            run_async_function(self.profile.update_async)
