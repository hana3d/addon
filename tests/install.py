import os
import sys

import addon_utils
import bpy

addon = f"hana3d_{os.getenv('HANA3D_ENV')}"
enable = addon_utils.enable(addon, default_set=True, persistent=True, handle_error=None)


if enable is None:
    sys.exit(1)
else:
    bpy.ops.wm.save_userpref()
