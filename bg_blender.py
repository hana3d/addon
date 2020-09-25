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

import os
import re
import sys
import threading

import bpy
from bpy.props import EnumProperty

from hana3d import utils, tasks_queue

bg_processes = []


class threadCom:  # object passed to threads to read background process stdout info
    ''' Object to pass data between thread and '''

    def __init__(
        self,
        eval_path_computing,
        eval_path_state,
        eval_path,
        process_type,
        proc,
        location=None,
        name='',
        eval_path_output=None,
    ):
        # self.obname=ob.name
        self.name = name
        self.eval_path_computing = eval_path_computing  # property that gets written to.
        self.eval_path_state = eval_path_state  # property that gets written to.
        self.eval_path = eval_path  # property checked when killing background process.
        self.eval_path_output = eval_path_output
        self.process_type = process_type
        self.progress_msg = None
        self.output_msg = None
        self.proc = proc
        self.lasttext = ''
        self.message = ''  # the message to be sent.
        self.progress = 0.0
        self.location = location
        self.error = False
        self.log = ''


def threadread(tcom: threadCom):
    '''reads stdout of background process, done this way to have it non-blocking.
    this threads basically waits for a stdout line to come in, fills the data, dies.'''
    while True:
        line = tcom.proc.stdout.readline()
        line = str(line)
        start = line.find('progress{')
        if start > -1:
            end = line.rfind('}')
            tcom.progress_msg = line[start + 9: end]
            if tcom.progress_msg.find('%') > -1:
                tcom.progress = float(re.findall(r'\d+\.\d+|\d+', tcom.progress_msg)[0])
            break
        start = line.find('write_output{')
        if start > -1:
            end = line.rfind('}')
            tcom.output_msg = line[start + 13: end]
            break
        if len(line) > 3:
            print(line, len(line))


class upload_in_chunks:
    def __init__(self, filename, chunksize=2 ** 20, report_name='file'):
        """Helper class that creates iterable for uploading file in chunks.
        Must be used only on background processes"""
        self.filename = filename
        self.chunksize = chunksize
        self.totalsize = os.path.getsize(filename)
        self.readsofar = 0
        self.report_name = report_name

    def __iter__(self):
        with open(self.filename, 'rb') as file:
            while True:
                data = file.read(self.chunksize)
                if not data:
                    sys.stderr.write("\n")
                    break
                self.readsofar += len(data)
                percent = 100 * self.readsofar / self.totalsize
                progress('uploading %s' % self.report_name, percent)
                # sys.stderr.write("\r{percent:3.0f}%".format(percent=percent))
                yield data

    def __len__(self):
        return self.totalsize


def progress(text, n=None):
    '''function for reporting during the script, works for background operations in the header.'''
    # for i in range(n+1):
    # sys.stdout.flush()
    text = str(text)
    if n is None:
        n = ''
    else:
        n = ' ' + ' ' + str(int(n * 1000) / 1000) + '% '
    sys.stdout.write('progress{%s%s}\n' % (text, n))
    sys.stdout.flush()


def write_output(text: str):
    '''Assign value to variable defined in threadCom's eval_path_output'''
    text = str(text)
    sys.stdout.write('write_output{%s}\n' % text)
    sys.stdout.flush()


# @bpy.app.handlers.persistent
def bg_update():
    '''monitoring of background process'''
    global bg_processes
    if len(bg_processes) == 0:
        return 2

    for p in bg_processes:
        readthread = p[0]
        tcom = p[1]
        if not readthread.is_alive():
            readthread.join()
            if tcom.error:
                exec(f'{tcom.eval_path_computing} = False')

            tcom.lasttext = tcom.progress_msg or ''
            if tcom.progress_msg is not None:
                exec(f'{tcom.eval_path_state} = tcom.progress_msg')
                tcom.progress_msg = None

            if 'finished successfully' in tcom.lasttext:
                bg_processes.remove(p)
                exec(f'{tcom.eval_path_computing} = False')
                tasks_queue.add_task((exec, (f'{tcom.eval_path_state} = ""',)), wait=5)
            else:
                readthread = threading.Thread(target=threadread, args=(tcom,), daemon=True)
                readthread.start()
                p[0] = readthread
    # if len(bg_processes) == 0:
    #     bpy.app.timers.unregister(bg_update)
    if len(bg_processes) > 0:
        return 0.3
    return 1.0


process_types = (
    ('UPLOAD', 'Upload', ''),
    ('THUMBNAILER', 'Thumbnailer', ''),
    ('RENDER', 'Render', ''),
)

process_sources = (
    ('MODEL', 'Model', 'set of objects'),
    ('SCENE', 'Scene', 'set of scenes'),
    ('MATERIAL', 'Material', 'any .blend Material'),
)


class KillBgProcess(bpy.types.Operator):
    '''Remove processes in background'''

    bl_idname = "object.kill_bg_process"
    bl_label = "Kill Background Process"
    bl_options = {'REGISTER'}

    process_type: EnumProperty(
        name="Type",
        items=process_types,
        description="Type of process",
        default="UPLOAD",
    )

    process_source: EnumProperty(
        name="Source",
        items=process_sources,
        description="Source of process",
        default="MODEL",
    )

    def execute(self, context):
        # first do the easy stuff...TODO all cases.
        props = utils.get_upload_props()
        if self.process_type == 'UPLOAD':
            props.uploading = False
        if self.process_type == 'THUMBNAILER':
            props.is_generating_thumbnail = False
        global hana3d_bg_process
        # print('killing', self.process_source, self.process_type)
        # then go kill the process. this wasn't working for unsetting props
        # and that was the reason for changing to the method above.

        processes = bg_processes
        for p in processes:
            tcom = p[1]
            if tcom.process_type == self.process_type:
                source = eval(tcom.eval_path)
                print(source.bl_rna.name, self.process_source)
                print(source.name)
                kill = False
                if source.bl_rna.name == 'Object' and self.process_source == 'MODEL':
                    if source.name == bpy.context.active_object.name:
                        kill = True
                if source.bl_rna.name == 'Material' and self.process_source == 'MATERIAL':
                    if source.name == bpy.context.active_object.active_material.name:
                        kill = True
                if kill:
                    estring = tcom.eval_path_computing + ' = False'
                    exec(estring)
                    processes.remove(p)
                    tcom.proc.kill()

        return {'FINISHED'}


def add_bg_process(
    location=None,
    name=None,
    eval_path_computing='',
    eval_path_state='',
    eval_path='',
    eval_path_output=None,
    process_type='',
    process=None,
):
    '''adds process for monitoring'''
    global bg_processes
    tcom = threadCom(
        eval_path_computing,
        eval_path_state,
        eval_path,
        process_type,
        process,
        location,
        name,
        eval_path_output,
    )
    readthread = threading.Thread(target=threadread, args=([tcom]), daemon=True)
    readthread.start()

    bg_processes.append([readthread, tcom])


def register():
    bpy.utils.register_class(KillBgProcess)
    bpy.app.timers.register(bg_update)


def unregister():
    if bpy.app.timers.is_registered(bg_update):
        bpy.app.timers.unregister(bg_update)
    bpy.utils.unregister_class(KillBgProcess)
