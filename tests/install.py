import addon_utils


if addon_utils.enable("asset-manager", default_set=False, persistent=True, handle_error=None) is None:
    exit(1)
