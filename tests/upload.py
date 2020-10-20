import sys
import time

import bpy

from hana3d import utils


def main():
    try:
        argv = sys.argv
        if "--" in argv:
            argv = argv[argv.index("--") + 1:]  # get all args after "--"
        else:
            argv = []

        props = utils.get_upload_props()
        print('Upload State: ', props.upload_state)
        print('Uploading: ', props.uploading)

        utils.update_profile()

        bpy.ops.object.select_all(action='DESELECT')

        obj = bpy.data.objects['Suzanne']
        obj.select_set(True)
        obj.hana3d.name = 'Suzanne'
        obj.hana3d.publish_message = 'Automated Test'
        obj.hana3d.thumbnail = '//Suzanne.jpg'
        print(obj.hana3d.workspace)
        bpy.ops.object.hana3d_upload(asset_type='MODEL')

        # while props.uploading:
        print('Upload State: ', props.upload_state)
        print('Uploading: ', props.uploading)
        # time.sleep(30)

        # print('Upload State: ', props.upload_state)

    except Exception as err:
        print(err, file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
