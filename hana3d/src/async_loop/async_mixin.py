"""Mixin to implement async Operators."""

import asyncio
import logging
import typing

import bpy

from ...config import HANA3D_NAME

MIXIN_TIMER = 1 / 15    # noqa: WPS432

log = logging.getLogger(__name__)


# noinspection PyAttributeOutsideInit
class AsyncModalOperatorMixin:  # noqa : WPS306,WPS214
    async_task = None  # asyncio task for fetching thumbnails
    signalling_future = None  # asyncio future for signalling that we want to cancel everything.
    log = logging.getLogger(f'{__name__}.AsyncModalOperatorMixin')

    _state = 'INITIALIZING'
    stop_upon_exception = False
    run_synchronously: bpy.props.BoolProperty(  # type: ignore
        name='run_synchronously',
        description='tells the operator to run synchronously',
        default=False,
    )

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
        return  # noqa: WPS324

    def quit(self):  # noqa: WPS125
        """Signals the state machine to stop this operator from running."""
        self._state = 'QUIT'    # noqa: WPS601

    def execute(self, context):
        """Mixin execute.

        Parameters:
            context: Blender context

        Returns:
            enum set in {‘RUNNING_MODAL’, ‘CANCELLED’, ‘FINISHED’, ‘PASS_THROUGH’, ‘INTERFACE’}
        """
        if self.run_synchronously:
            loop = asyncio.get_event_loop()
            loop.run_until_complete(self.async_execute(context))
            return {'FINISHED'}

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
                self._state = 'EXCEPTION'   # noqa: WPS601
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
        """Stop the currently running async task, and starts another one.

        Parameters:
            async_task: new async task
            future: asyncio future for signalling that we want to cancel everything
        """
        self.log.debug(f'Setting up a new task {async_task}, so any existing task must be stopped')
        self._stop_async_task()

        # Download the previews asynchronously.
        self.signalling_future = future or asyncio.Future()  # noqa: WPS601
        self.async_task = asyncio.ensure_future(async_task)  # noqa: WPS601
        self.log.debug(f'Created new task {self.async_task}')

        # Start the async manager so everything happens.
        self.log.debug('Starting asyncio loop')
        operator = getattr(bpy.ops.asyncio, f'{HANA3D_NAME}_loop')
        async_result = operator()
        self.log.debug(f'Result of starting modal operator is {async_result}')

    def _stop_async_task(self):  # noqa: WPS213
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
        except Exception as error:
            self.log.exception('Exception from asynchronous task')
            self.log.debug(error)
