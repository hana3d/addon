import pathlib
import subprocess


def run_blender_script(
        script_path: pathlib.Path,
        *args,
        blend_file: pathlib.Path = None,
        addons: list = None,
        timeout: int = None
) -> str:
    cmd = ['blender']
    if blend_file is not None:
        cmd.append(blend_file)
    cmd.extend(['-noaudio', '-b'])
    if addons:
        cmd.extend(['--addons', ','.join(addons)])
    cmd.extend(['-P', script_path, '--', *args])

    run = subprocess.run(cmd, timeout=timeout, capture_output=True)
    if run.returncode != 0:
        error_msg = run.stderr.decode()
        raise Exception('Blender script raised error:\n' + error_msg)
