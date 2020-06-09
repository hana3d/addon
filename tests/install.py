import addon_utils


if addon_utils.enable("asset_manager_real2u", default_set=False, persistent=True, handle_error=None) is None:
    exit(1)
