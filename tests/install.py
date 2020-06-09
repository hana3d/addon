import addon_utils


if addon_utils.enable("blenderkit", default_set=True, persistent=True, handle_error=None) is None:
    exit(1)
