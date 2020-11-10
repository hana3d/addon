import sys

import addon_utils
import bpy


enable = addon_utils.enable("hana3d_production", default_set=True, persistent=True, handle_error=None)

if enable is None:
    sys.exit(1)
else:
    bpy.ops.wm.save_userpref()
