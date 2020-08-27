# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

if 'bpy' in locals():
    from importlib import reload

    utils = reload(utils)
else:
    from hana3d import utils

import bpy


def check_meshprops(props, obs):
    ''' checks polycount '''
    fc = 0
    fcr = 0

    for ob in obs:
        if ob.type == 'MESH' or ob.type == 'CURVE':
            ob_eval = None
            if ob.type == 'CURVE':
                # depsgraph = bpy.context.evaluated_depsgraph_get()
                # object_eval = ob.evaluated_get(depsgraph)
                mesh = ob.to_mesh()
            else:
                mesh = ob.data
            fco = len(mesh.polygons)
            fc += fco
            fcor = fco

            for m in ob.modifiers:
                if m.type == 'SUBSURF' or m.type == 'MULTIRES':
                    fcor *= 4 ** m.render_levels
                # this is rough estimate, not to waste time with evaluating all nonmanifold edges
                if m.type == 'SOLIDIFY':
                    fcor *= 2
                if m.type == 'ARRAY':
                    fcor *= m.count
                if m.type == 'MIRROR':
                    fcor *= 2
                if m.type == 'DECIMATE':
                    fcor *= m.ratio
            fcr += fcor

            if ob_eval:
                ob_eval.to_mesh_clear()

    # write out props
    props.face_count = fc
    props.face_count_render = fcr


def countObs(props, obs):
    ob_types = {}
    count = len(obs)
    for ob in obs:
        otype = ob.type.lower()
        ob_types[otype] = ob_types.get(otype, 0) + 1
    props.object_count = count


def get_autotags():
    """ call all analysis functions """
    ui = bpy.context.scene.Hana3DUI
    if ui.asset_type == 'MODEL':
        ob = utils.get_active_model()
        obs = utils.get_hierarchy(ob)
        props = ob.hana3d
        if props.name == "":
            props.name = ob.name

        dim, bbox_min, bbox_max = utils.get_dimensions(obs)
        props.dimensions = dim
        props.bbox_min = bbox_min
        props.bbox_max = bbox_max

        check_meshprops(props, obs)
        countObs(props, obs)


class AutoFillTags(bpy.types.Operator):
    """Fill tags for asset. Now run before upload, no need to interact from user side."""

    bl_idname = "object.hana3d_auto_tags"
    bl_label = "Generate Auto Tags for hana3d"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    @classmethod
    def poll(cls, context):
        return bpy.context.view_layer.objects.active is not None

    def execute(self, context):
        get_autotags()
        return {'FINISHED'}


def register():
    bpy.utils.register_class(AutoFillTags)


def unregister():
    bpy.utils.unregister_class(AutoFillTags)


if __name__ == "__main__":
    register()
