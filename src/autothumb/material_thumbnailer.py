import math
import uuid

import bpy
import bmesh
from mathutils import Euler, Vector

from .. import async_loop
from ... import paths, utils
from ...config import HANA3D_DESCRIPTION, HANA3D_NAME
# from ...report_tools import execute_wrapper

BACKGROUND_DEFAULT_COLOR = (1, 1, 1, 1)
CAMERA_DEFAULT_LOCATION = (-3.1068, -3.14043, 2.3688)
CAMERA_DEFAULT_ROTATION = (1.1122483015060425, -8.048914423852693e-08, -0.7800155878067017)
LIGHT_DEFAULT_LOCATION = (2, -4.76656, 3.33653)


class MaterialThumbnailerOperator(async_loop.AsyncModalOperatorMixin, bpy.types.Operator):
    """Generate Cycles thumbnail for model assets"""

    bl_idname = f'material.{HANA3D_NAME}_thumbnail'
    bl_label = f'{HANA3D_DESCRIPTION} Thumbnail Generator'
    bl_options = {'REGISTER', 'INTERNAL'}

    async def prepare_scene(self, context):
        self.scene = bpy.data.scenes.new('thumbnailer_scene')

        self.world = bpy.data.worlds.new('thumbnailer_world')
        self.world.use_nodes = True
        node_tree = self.world.node_tree
        node_tree.nodes['Background'].inputs['Color'].default_value = BACKGROUND_DEFAULT_COLOR
        self.scene.world = self.world

        self.light_data = bpy.data.lights.new('thumbnailer_light_data', 'POINT')
        self.light = bpy.data.objects.new('thumbnailer_light', self.light_data)
        self.light_axis = bpy.data.objects.new('thumbnailer_light_axis', None)
        self.scene.collection.objects.link(self.light)
        self.scene.collection.objects.link(self.light_axis)
        self.light.location.x = LIGHT_DEFAULT_LOCATION[0]
        self.light.location.y = LIGHT_DEFAULT_LOCATION[1]
        self.light.location.z = LIGHT_DEFAULT_LOCATION[2]
        self.light.parent = self.light_axis

        self.camera_data = bpy.data.cameras.new('thumbnailer_camera_data')
        self.camera = bpy.data.objects.new('thumbnailer_camera', self.camera_data)
        self.camera_axis = bpy.data.objects.new('thumbnailer_camera_axis', None)
        self.scene.collection.objects.link(self.camera)
        self.scene.collection.objects.link(self.camera_axis)
        self.scene.camera = self.camera
        self.camera.location.x = CAMERA_DEFAULT_LOCATION[0]
        self.camera.location.y = CAMERA_DEFAULT_LOCATION[1]
        self.camera.location.z = CAMERA_DEFAULT_LOCATION[2]
        self.camera.rotation_mode = 'XYZ'
        self.camera.rotation_euler = Euler(CAMERA_DEFAULT_ROTATION, 'XYZ')
        self.camera.parent = self.camera_axis

        self.scene.render.engine = 'CYCLES'
        if context.preferences.addons[HANA3D_NAME].preferences.thumbnail_use_gpu:
            self.scene.cycles.device = 'GPU'
        self.scene.render.resolution_x = 512
        self.scene.render.resolution_y = 512
        self.scene.render.image_settings.file_format = 'JPEG'

    async def add_material_sphere(self, material):
        self.sphere_data = bpy.data.meshes.new('thumbnailer_sphere_data')
        self.sphere = bpy.data.objects.new('thumbnailer_sphere', self.sphere_data)

        bm = bmesh.new()
        bmesh.ops.create_uvsphere(bm, u_segments=32, v_segments=16, diameter=1)
        bm.to_mesh(self.sphere_data)
        bm.free()

        self.sphere.active_material = material

        self.scene.collection.objects.link(self.sphere)

    async def center_objs_for_thumbnail(self):
        self.sphere.rotation_euler = (0, 0, 0)

        minx, miny, minz, maxx, maxy, maxz = utils.get_bounds_worldspace(self.copies)

        cx = (maxx - minx) / 2 + minx
        cy = (maxy - miny) / 2 + miny

        self.sphere.location += Vector((-cx, -cy, -minz))

        self.camera.location.z = (maxz - minz) / 2
        self.light.location.z = (maxz - minz) / 2
        dx = maxx - minx
        dy = maxy - miny
        dz = maxz - minz
        r = math.sqrt(dx * dx + dy * dy + dz * dz)

        coef = 0.7
        r *= coef
        self.camera.scale = (r, r, r)
        self.light.scale = (r, r, r)
        bpy.context.view_layer.update()

    async def render(self):
        filepath = f'{paths.get_temp_dir("thumbnailer")}/{uuid.uuid4()}.png'
        self.scene.render.filepath = filepath
        bpy.ops.render.render(write_still=True, animation=False, scene=self.scene.name)

    async def remove_scene(self):
        bpy.data.objects.remove(self.sphere)
        bpy.data.mesh.remove(self.sphere_data)
        bpy.data.worlds.remove(self.world)
        bpy.data.objects.remove(self.camera_axis)
        bpy.data.objects.remove(self.camera)
        bpy.data.cameras.remove(self.camera_data)
        bpy.data.objects.remove(self.light_axis)
        bpy.data.objects.remove(self.light)
        bpy.data.lights.remove(self.light_data)
        bpy.data.scenes.remove(self.scene)

    async def async_execute(self, context):

        material = utils.get_active_material(context)
        props = getattr(model, HANA3D_NAME)
        props.is_generating_thumbnail = True
        props.thumbnail_generating_state = 'preparing thumbnail scene'
        await self.prepare_scene(context)
        props.thumbnail_generating_state = 'creating material sphere'
        await self.copy_objects(material)
        props.thumbnail_generating_state = 'positioning objects'
        await self.center_objs_for_thumbnail()
        props.thumbnail_generating_state = 'rendering thumbnail'
        await self.render()
        props.thumbnail_generating_state = 'cleaning duplicates'
        await self.remove_scene()
        props.thumbnail_generating_state = 'thumbnailer finished successfully'
        props.is_generating_thumbnail = False

        self._state = 'QUIT'


def register():
    bpy.utils.register_class(MaterialThumbnailerOperator)


def unregister():
    bpy.utils.unregister_class(MaterialThumbnailerOperator)
