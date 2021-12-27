"""Hana3D subprocess async."""

import asyncio
import logging
from typing import List


class Subprocess(object):  # noqa : WPS214
    """Hana3D subprocess async."""

    def __init__(self):
        """Create a Subprocess object."""

    async def _read_stream(self, stream, cb):
        while True:
            line = await stream.readline()
            if line:
                cb(line)
            else:
                break

    async def subprocess(self, cmd: List[str]):    # noqa : WPS210
        """Run a command in a non-blocking subprocess.

        Parameters:
            cmd: command to be executed.

        Returns:
            subprocess.CompletedProcess: the return value representing a process that has finished.

        Raises:
            Exception: Subprocess exited in error
        """
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE)

        await asyncio.wait([
            self._read_stream(proc.stdout, lambda x: logging.debug(f'[stdout]\n{x.decode()}')),
            self._read_stream(proc.stderr, lambda x: logging.debug(f'[stderr]\n{x.decode()}')),
        ])

        return await proc.wait()
