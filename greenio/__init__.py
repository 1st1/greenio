##
# Copyright (c) 2013 Yury Selivanov
# License: Apache 2.0
##

"""greenio package allows to compose greenlets and asyncio coroutines."""

__all__ = ['task', 'yield_from']


import greenlet
import sys

try:
    import asyncio
except ImportError:
    asyncio = None
try:
    import trollius
except ImportError:
    trollius = None
    if asyncio is None:
        raise
if asyncio is None:
    asyncio = trollius

def _create_task(coro, loop):
    if loop is None:
        loop = asyncio.get_event_loop()
    if hasattr(loop, 'create_task'):
        return loop.create_task(coro)
    else:
        return GreenTask(coro, loop=loop)


if trollius is not None:
    def _async(future, loop):
        # trollius iscoroutine() accepts trollius and asyncio coroutine
        # objects
        if trollius.iscoroutine(future):
            return _create_task(future, loop)
        else:
            return future
else:
    def _async(future, loop):
        if asyncio.iscoroutine(future):
            return _create_task(future, loop)
        else:
            return future


_FUTURE_CLASSES = (asyncio.Future,)
if trollius is not None and trollius is not asyncio:
    _FUTURE_CLASSES += (trollius.Future,)

import sys


class _LoopGreenlet(greenlet.greenlet):
    """Main greenlet (analog to main thread) for the event-loop.

    It's a policy task to provide event-loop implementation with
    its "run_*" methods executed in _LoopGreenlet context"""


class _TaskGreenlet(greenlet.greenlet):
    """Each task (and its subsequent coroutines) decorated with
    ``@greenio.task`` is executed in this greenlet"""


class _GreenTaskMixin(object):
    def __init__(self, *args, **kwargs):
        self._greenlet = None
        super(_GreenTaskMixin, self).__init__(*args, **kwargs)

    def _step(self, value=None, exc=None):
        if self._greenlet is None:
            # Means that the task is not currently in a suspended greenlet
            # waiting for results for "yield_from"
            ovr = super(_GreenTaskMixin, self)._step
            self._greenlet = _TaskGreenlet(ovr)

            # Store a reference to the current task for "yield_from"
            self._greenlet.task = self

            # Now invoke overloaded "Task._step" in "_TaskGreenlet"
            result = self._greenlet.switch(value, exc)

            # If "result" is "_YIELDED" it means that the "yield_from"
            # method was called
            if result is not _YIELDED:
                # And if not - then task jumped out of greenlet without
                # calling "yield_from"
                self._greenlet.task = None
                self._greenlet = None
            else:
                self.__class__._current_tasks.pop(self._loop)
        else:
            # The task is in the greenlet, that means that we have a result
            # for the "yield_from"

            self.__class__._current_tasks[self._loop] = self

            if exc is not None:
                if hasattr(exc, '__traceback__'):
                    tb = exc.__traceback__
                else:
                    tb = sys.exc_info()[2]
                result = self._greenlet.throw(
                    type(exc), exc, tb)
            else:
                result = self._greenlet.switch(value)

            # Again, if "result" is "_YIELDED" then we just called "yield_from"
            # again
            if result is not _YIELDED:
                self._greenlet.task = None
                self._greenlet = None
            else:
                self.__class__._current_tasks.pop(self._loop)


class _GreenLoopMixin(object):
    def _green_run(self, method, args, kwargs):
        return _LoopGreenlet(method).switch(*args, **kwargs)

    def run_until_complete(self, *args, **kwargs):
        ovr = super(_GreenLoopMixin, self).run_until_complete
        return self._green_run(ovr, args, kwargs)

    def run_forever(self, *args, **kwargs):
        ovr = super(_GreenLoopMixin, self).run_forever
        return self._green_run(ovr, args, kwargs)


class GreenTask(_GreenTaskMixin, asyncio.Task):
    pass


class GreenUnixSelectorLoop(_GreenLoopMixin, asyncio.SelectorEventLoop):
    def create_task(self, coro):
        return GreenTask(coro, loop=self)


class GreenEventLoopPolicy(asyncio.DefaultEventLoopPolicy):
    def new_event_loop(self):
        return GreenUnixSelectorLoop()


if trollius is not None:
    if trollius is not asyncio:
        class GreenTrolliusTask(_GreenTaskMixin, trollius.Task):
            pass

        class GreenTrolliusUnixSelectorLoop(_GreenLoopMixin,
                                            trollius.SelectorEventLoop):
            def create_task(self, coro):
                return GreenTrolliusTask(coro)

        class GreenTrolliusEventLoopPolicy(asyncio.DefaultEventLoopPolicy):

            def new_event_loop(self):
                return GreenTrolliusUnixSelectorLoop()
    else:
        GreenTrolliusTask = GreenTask
        GreenTrolliusUnixSelectorLoop = GreenUnixSelectorLoop
        GreenTrolliusEventLoopPolicy = GreenEventLoopPolicy


def yield_from(future, loop=None):
    """A function to use instead of ``yield from`` statement."""

    future = _async(future, loop)

    gl = greenlet.getcurrent()

    if __debug__:
        if not isinstance(gl.parent, _LoopGreenlet):
            raise RuntimeError(
                '"greenio.yield_from" requires GreenEventLoopPolicy '
                'or compatible')
            # or something went horribly wrong...

        if not isinstance(gl, _TaskGreenlet):
            raise RuntimeError(
                '"greenio.yield_from" was supposed to be called from a '
                '"greenio.task" or a subsequent coroutine')
            # ...ditto

    task = gl.task

    if not isinstance(future, _FUTURE_CLASSES):
        raise RuntimeError(
            'greenlet.yield_from was supposed to receive only Futures, '
            'got {!r} in task {!r}'.format(future, task))

    # "_wakeup" will call the "_step" method (which we overloaded in
    # GreenTask, and therefore wakeup the awaiting greenlet)
    future.add_done_callback(task._wakeup)
    task._fut_waiter = future

    # task cancellation has been delayed.
    if task._must_cancel:
        if task._fut_waiter.cancel():
            task._must_cancel = False

    # Jump out of the current task greenlet (we'll return to GreenTask._step)
    return gl.parent.switch(_YIELDED)


def task(func, loop=None):
    """A decorator, allows use of ``yield_from`` in the decorated or
    subsequent coroutines."""

    coro_func = asyncio.coroutine(func)

    def task_wrapper(*args, **kwds):
        coro_obj = coro_func(*args, **kwds)
        return _create_task(coro_obj, loop)

    return task_wrapper


class _YIELDED(object):
    """Marker, don't use it"""
