import json
import pdb
import unittest
from os.path import dirname, join

import bpy

from hana3d_dev.src.validators.uv_check import uv_checker

tests = [
    {
        'export_data': {
            'models': ['Cube'],
            'type': 'MODEL'
        },
        'expected_result': (True, 'No duplicated UVs detected!')
    },
    {
        'export_data': {
            'material': 'Material.002',
            'type': 'MATERIAL'
        },
        'expected_result': (True, 'No duplicated UVs detected!')
    },
    {
        'export_data': {
            'scene': 'Scene',
            'type': 'SCENE'
        },
        'expected_result': (False, 'Meshes with more than 1 UV Map: Torus')
    },
        {
        'export_data': {
            'models': ['Thing', 'Armature', 'Torus'],
            'type': 'MODEL'
        },
        'expected_result': (False, 'Meshes with more than 1 UV Map: Torus')
    },
]




class TestUVCheck(unittest.TestCase):
    def test_validate(self):
        bpy.ops.wm.open_mainfile(filepath=join(dirname(__file__), '../scenes/uv_check.blend'))
        for test in tests:
            uv_checker.run_validation(test['export_data'])
            test_result = uv_checker.get_validation_result()
            self.assertTrue(test_result == test['expected_result'])

    # def test_fix(self):
    #     bpy.wm.open_mainfile(join(dirname(__file__), '../scenes/uv_check.blend'))
    #     self.assertEqual(btools.utils.minmax(range(10)), (0, 9))
    #     self.assertEqual(btools.utils.minmax([-1, 0]), (-1, 0))

    #     # -- test with keyfunction
    #     vecs = [Vector(tup) for tup in zip(range(10), range(10, 0, -1))]
    #     res = btools.utils.minmax(vecs, key=lambda v: v.y)
    #     self.assertEqual(res[0], Vector((9.0, 1.0)))
    #     self.assertEqual(res[1], Vector((0.0, 10.0)))
