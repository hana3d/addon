"""Hana3D authentication using Auth0."""

import time

from ...hana3d_oauth import refresh_token
from ..preferences.preferences import Preferences
from ..preferences.profile import Profile
from ...utils import update_profile_async


class Authentication(object):
    """Hana3D authentication."""

    def __init__(self):
        """Create an Authentication object."""
        self.preferences = Preferences()
        self.profile = Profile()

    def refresh_token_timer(self):
        """Refresh the API key token.

        Returns:
            str: api_key_life
        """
        print('refresh_token_timer')  # noqa: WPS421
        self.update_tokens()
        return self.preferences.user_preferences().api_key_life

    def update_tokens(self):
        """Refresh the API key token."""
        api_key_exists = self.preferences.user_preferences().api_key
        api_key_has_timed_out = self.preferences.user_preferences().api_key_timeout < time.time()
        if (api_key_exists and api_key_has_timed_out):
            refresh_token(immediate=False)
        if api_key_exists and self.profile.user_profile() is None:
            update_profile_async()
