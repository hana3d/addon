import os
import sys
from importlib import import_module

import bpy

from libs.paths import get_addon_name

module = import_module(get_addon_name())

utils = module.utils


def main():
    try:
        argv = sys.argv
        if "--" in argv:
            argv = argv[argv.index("--") + 1:]  # get all args after "--"
        else:
            argv = []

        utils.update_profile()

        bpy.ops.object.select_all(action='DESELECT')

        obj = bpy.data.objects['Suzanne']
        obj.select_set(True)
        props = getattr(obj, get_addon_name())
        props.name = 'Suzanne'
        props.description = f'{os.getenv("HANA3D_ENV")} Test'
        props.publish_message = f'{os.getenv("HANA3D_ENV")} Test'
        props.thumbnail = '//Suzanne.jpg'
        upload_op = getattr(bpy.ops.object, f'{get_addon_name()}_upload')
        upload_op(asset_type='MODEL')

    except Exception as err:
        print(err, file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
