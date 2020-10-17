import sys

import bpy
import addon_utils

enable = addon_utils.enable("hana3d", default_set=True, persistent=True, handle_error=None)

if enable is None:
    sys.exit(1)
else:
    bpy.ops.wm.save_userpref()
