"""Manages the asyncio loop."""

import asyncio
import gc
import logging
import sys
import traceback
import typing
from concurrent import futures

import bpy

from ...config import HANA3D_NAME
from .loop_status import LoopStatus

MODAL_TIMER = 0.00001

log = logging.getLogger(__name__)

# Keeps track of whether a loop-kicking operator is already running.
_loop_kicking_operator_running = False


def setup_asyncio_executor():
    """Set up AsyncIO to run properly on each platform."""
    if sys.platform == 'win32':
        asyncio.get_event_loop().close()
        # On Windows, the default event loop is SelectorEventLoop, which does
        # not support subprocesses. ProactorEventLoop should be used instead.
        # Source: https://docs.python.org/3/library/asyncio-subprocess.html
        loop = asyncio.ProactorEventLoop()
        asyncio.set_event_loop(loop)
    else:
        loop = asyncio.get_event_loop()

    executor = futures.ThreadPoolExecutor(max_workers=10)
    loop.set_default_executor(executor)


def kick_async_loop() -> bool:  # noqa : WPS210,WPS213,WPS231
    """Performs a single iteration of the asyncio event loop.

    Returns:
        bool: whether the asyncio loop should stop after this kick.
    """
    loop = asyncio.get_event_loop()

    # Even when we want to stop, we always need to do one more
    # 'kick' to handle task-done callbacks.
    stop_after_this_kick = False

    if loop.is_closed():
        log.warning('loop closed, stopping immediately.')
        return True

    all_tasks = asyncio.Task.all_tasks()
    if not len(all_tasks):
        log.debug('no more scheduled tasks, stopping after this kick.')
        stop_after_this_kick = True

    elif all(task.done() for task in all_tasks):
        log.debug(
            f'all {len(all_tasks)} tasks are done, fetching results and stopping after this kick.',
        )
        stop_after_this_kick = True

        # Clean up circular references between tasks.
        gc.collect()

        for task_idx, task in enumerate(all_tasks):
            if not task.done():
                continue

            # noinspection PyBroadException
            try:
                res = task.result()
            except asyncio.CancelledError:
                # No problem, we want to stop anyway.
                log.debug(f'   task #{task_idx}: cancelled')
            except Exception:
                log.debug(f'{task}: resulted in exception')
                traceback.print_exc()
            log.debug(f'   task #{task_idx}: result={res}')

    loop.stop()
    loop.run_forever()

    return stop_after_this_kick


def ensure_async_loop():
    """Execute async tasks in event loop through `AsyncLoopModalOperator`."""
    log.debug('Starting asyncio loop')
    operator = getattr(bpy.ops.asyncio, f'{HANA3D_NAME}_loop')
    async_result = operator()
    log.debug(f'Result of starting modal operator is {async_result}')


def erase_async_loop():
    """Force stop event loop."""
    log.debug('Erasing async loop')

    loop = asyncio.get_event_loop()
    loop.stop()


def run_async_function(
    async_function: typing.Callable,
    done_callback: typing.Optional[typing.Callable] = None,
    **kwargs,
):
    """Start an asynchronous task from an async function.

    Args:
        async_function: async function to run in event loop.
        done_callback: callback function to be called when `async_function` is done.
        kwargs: arguments to pass to `async_function`

    def done_callback(task):
        print('Task result: ', task.result())
    """
    log.debug(f'Running async function {async_function}')

    async_task = asyncio.ensure_future(async_function(**kwargs))
    if done_callback is not None:
        async_task.add_done_callback(done_callback)
    ensure_async_loop()


class AsyncLoopModalOperator(bpy.types.Operator):
    """Modal that runs the asyncio main loop."""

    bl_idname = f'asyncio.{HANA3D_NAME}_loop'
    bl_label = 'Runs the asyncio main loop'

    timer = None
    log = logging.getLogger(f'{__name__}.AsyncLoopModalOperator')

    def __init__(self):
        self.loop_status = LoopStatus()

    def __del__(self):  # noqa: WPS603
        """Stop loop-kicking operator.

        This can be required when the operator is running while Blender
        (re)loads a file. The operator then doesn't get the chance to
        finish the async tasks, hence stop_after_this_kick is never True.
        """
        self.loop_status.update_operator_status(False)

    def execute(self, context):
        """Modal execute just calls invoke.

        Parameters:
            context: Blender context

        Returns:
            enum set in {‘RUNNING_MODAL’, ‘CANCELLED’, ‘FINISHED’, ‘PASS_THROUGH’, ‘INTERFACE’}
        """
        return self.invoke(context, None)

    def invoke(self, context, event):
        """Set up loop-kicking operator.

        Parameters:
            context: Blender context
            event: invoke event

        Returns:
            enum set in {‘RUNNING_MODAL’, ‘CANCELLED’, ‘FINISHED’, ‘PASS_THROUGH’, ‘INTERFACE’}
        """
        if self.loop_status.get_operator_status():
            self.log.debug('Another loop-kicking operator is already running.')
            return {'PASS_THROUGH'}

        context.window_manager.modal_handler_add(self)
        self.loop_status.update_operator_status(True)

        wm = context.window_manager
        self.timer = wm.event_timer_add(MODAL_TIMER, window=context.window)  # noqa: WPS601

        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        """Loop-kicking operator modal.

        Parameters:
            context: Blender context
            event: invoke event

        Returns:
            enum set in {‘RUNNING_MODAL’, ‘CANCELLED’, ‘FINISHED’, ‘PASS_THROUGH’, ‘INTERFACE’}

        If self.loop_status.get_operator_status() is set to False, someone called
        erase_async_loop(). This is a signal that we really should stop running.
        """
        if not self.loop_status.get_operator_status():
            return {'FINISHED'}

        if event.type != 'TIMER':
            return {'PASS_THROUGH'}

        stop_after_this_kick = kick_async_loop()
        if stop_after_this_kick:
            context.window_manager.event_timer_remove(self.timer)
            self.loop_status.update_operator_status(False)

            self.log.debug('Stopped asyncio loop kicking')
            return {'FINISHED'}

        return {'RUNNING_MODAL'}


def register():
    """Async loop register."""
    setup_asyncio_executor()
    bpy.utils.register_class(AsyncLoopModalOperator)


def unregister():
    """Async loop unregister."""
    bpy.utils.unregister_class(AsyncLoopModalOperator)
