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

MODAL_TIMER = 0.00001
MIXIN_TIMER = 1 / 15    # noqa: WPS432

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
    global _loop_kicking_operator_running   # noqa: WPS420

    log.debug('Erasing async loop')

    loop = asyncio.get_event_loop()
    loop.stop()


def run_async_function(
    async_function: typing.Callable,
    done_callback: typing.Optional[typing.Callable[[typing.Callable], typing.Any]] = None,
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

    def __del__(self):  # noqa: WPS603
        """Stop loop-kicking operator."""
        global _loop_kicking_operator_running   # noqa: WPS420

        # This can be required when the operator is running while Blender
        # (re)loads a file. The operator then doesn't get the chance to
        # finish the async tasks, hence stop_after_this_kick is never True.
        _loop_kicking_operator_running = False  # noqa: WPS122,WPS442

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
        global _loop_kicking_operator_running   # noqa: WPS420

        if _loop_kicking_operator_running:  # noqa: WPS122,WPS442
            self.log.debug('Another loop-kicking operator is already running.')
            return {'PASS_THROUGH'}

        context.window_manager.modal_handler_add(self)
        _loop_kicking_operator_running = True   # noqa: WPS122,WPS442

        wm = context.window_manager
        self.timer = wm.event_timer_add(MODAL_TIMER, window=context.window)

        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        """Loop-kicking operator modal.

        Parameters:
            context: Blender context
            event: invoke event

        Returns:
            enum set in {‘RUNNING_MODAL’, ‘CANCELLED’, ‘FINISHED’, ‘PASS_THROUGH’, ‘INTERFACE’}
        """
        global _loop_kicking_operator_running   # noqa: WPS420

        # If _loop_kicking_operator_running is set to False, someone called
        # erase_async_loop(). This is a signal that we really should stop
        # running.
        if not _loop_kicking_operator_running:  # noqa: WPS122,WPS442
            return {'FINISHED'}

        if event.type != 'TIMER':
            return {'PASS_THROUGH'}

        stop_after_this_kick = kick_async_loop()
        if stop_after_this_kick:
            context.window_manager.event_timer_remove(self.timer)
            _loop_kicking_operator_running = False  # noqa: WPS122,WPS442

            self.log.debug('Stopped asyncio loop kicking')
            return {'FINISHED'}

        return {'RUNNING_MODAL'}


# noinspection PyAttributeOutsideInit
class AsyncModalOperatorMixin:  # noqa : WPS306,WPS214
    async_task = None  # asyncio task for fetching thumbnails
    signalling_future = None  # asyncio future for signalling that we want to cancel everything.
    log = logging.getLogger(f'{__name__}.AsyncModalOperatorMixin')

    _state = 'INITIALIZING'
    stop_upon_exception = False

    def invoke(self, context, event):
        """Mixin invoke.

        Parameters:
            context: Blender context
            event: invoke event

        Returns:
            enum set in {‘RUNNING_MODAL’, ‘CANCELLED’, ‘FINISHED’, ‘PASS_THROUGH’, ‘INTERFACE’}
        """
        context.window_manager.modal_handler_add(self)
        self.timer = context.window_manager.event_timer_add(MIXIN_TIMER, window=context.window)

        self.log.info('Starting')
        self._new_async_task(self.async_execute(context))

        return {'RUNNING_MODAL'}

    async def async_execute(self, context):
        """Entry point of the asynchronous operator.

        Implement in a subclass.

        Parameters:
            context: Blender context
        """
        return

    def quit(self):
        """Signals the state machine to stop this operator from running."""
        self._state = 'QUIT'

    def execute(self, context):
        """Mixin execute.

        Parameters:
            context: Blender context

        Returns:
            enum set in {‘RUNNING_MODAL’, ‘CANCELLED’, ‘FINISHED’, ‘PASS_THROUGH’, ‘INTERFACE’}
        """
        return self.invoke(context, None)

    def modal(self, context, event):
        """Mixin modal.

        Parameters:
            context: Blender context
            event: invoke event

        Returns:
            enum set in {‘RUNNING_MODAL’, ‘CANCELLED’, ‘FINISHED’, ‘PASS_THROUGH’, ‘INTERFACE’}
        """
        task = self.async_task

        if self._state != 'EXCEPTION' and task and task.done() and not task.cancelled():
            ex = task.exception()
            if ex is not None:
                self._state = 'EXCEPTION'
                self.log.error(f'Exception while running task: {ex}')
                if self.stop_upon_exception:
                    self.quit()
                    self._finish(context)
                    return {'FINISHED'}

                return {'RUNNING_MODAL'}

        if self._state == 'QUIT':
            self._finish(context)
            return {'FINISHED'}

        return {'PASS_THROUGH'}

    def _finish(self, context):
        self._stop_async_task()
        context.window_manager.event_timer_remove(self.timer)

    def _new_async_task(self, async_task: typing.Coroutine, future: asyncio.Future = None):
        """Stops the currently running async task, and starts another one."""

        self.log.debug(f'Setting up a new task {async_task}, so any existing task must be stopped')
        self._stop_async_task()

        # Download the previews asynchronously.
        self.signalling_future = future or asyncio.Future()
        self.async_task = asyncio.ensure_future(async_task)
        self.log.debug(f'Created new task {self.async_task}')

        # Start the async manager so everything happens.
        ensure_async_loop()

    def _stop_async_task(self):
        self.log.debug('Stopping async task')
        if self.async_task is None:
            self.log.debug('No async task, trivially stopped')
            return

        # Signal that we want to stop.
        self.async_task.cancel()
        if not self.signalling_future.done():
            self.log.info('Signalling that we want to cancel anything that is running.')
            self.signalling_future.cancel()

        # Wait until the asynchronous task is done.
        if not self.async_task.done():
            self.log.info('blocking until async task is done.')
            loop = asyncio.get_event_loop()
            try:
                loop.run_until_complete(self.async_task)
            except asyncio.CancelledError:
                self.log.info('Asynchronous task was cancelled')
                return

        # noinspection PyBroadException
        try:
            self.async_task.result()  # This re-raises any exception of the task.
        except asyncio.CancelledError:
            self.log.info('Asynchronous task was cancelled')
        except Exception:
            self.log.exception('Exception from asynchronous task')


def register():
    """Async loop register."""
    setup_asyncio_executor()
    bpy.utils.register_class(AsyncLoopModalOperator)


def unregister():
    """Async loop unregister."""
    bpy.utils.unregister_class(AsyncLoopModalOperator)
