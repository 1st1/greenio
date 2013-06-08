##
# Copyright (c) 2013 Yury Selivanov
# License: Apache 2.0
##


"""greentulip package allows to compose greenlets and tulip coroutines."""


__all__ = 'task', 'yield_from'


import greenlet
import tulip
from tulip import unix_events, tasks, futures


class _LoopGreenlet(greenlet.greenlet):
    """Main greenlet (analolg to main thread) for the event-loop"""


class _TaskGreenlet(greenlet.greenlet):
    """Each task (and its subsequent coroutines) decorated with
    ``@greentulip.task`` is executed in this greenlet"""


class GreenTask(tulip.Task):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._greenlet = None

    def _step(self, value=tasks._marker, exc=None):
        if self._greenlet is None:
            ovr = super()._step
            self._greenlet = _TaskGreenlet(ovr)
            self._greenlet.task = self
            result = self._greenlet.switch(value, exc)
            if result is not _YIELDED:
                self._greenlet.task = None
                self._greenlet = None
        else:
            if exc is not None:
                result = self._greenlet.throw(type(exc), exc, exc.__traceback__)
            else:
                result = self._greenlet.switch(value)
            if result is not _YIELDED:
                self._greenlet.task = None
                self._greenlet = None


class _GreenLoopMixin:
    def _green_run(self, method, args, kwargs):
        return _LoopGreenlet(method).switch(*args, **kwargs)

    def run_until_complete(self, *args, **kwargs):
        ovr = super().run_until_complete
        return self._green_run(ovr, args, kwargs)

    def run_once(self, *args, **kwargs):
        ovr = super().run_once
        return self._green_run(ovr, args, kwargs)

    def run_forever(self, *args, **kwargs):
        ovr = super().run_forever
        return self._green_run(ovr, args, kwargs)


class GreenUnixSelectorLoop(_GreenLoopMixin, unix_events.SelectorEventLoop):
    pass


class GreenEventLoopPolicy(tulip.DefaultEventLoopPolicy):
    def new_event_loop(self):
        return GreenUnixSelectorLoop()


def yield_from(future):
    """A function to use instead of ``yield from`` statement.
    """

    gl = greenlet.getcurrent()

    if __debug__:
        if not isinstance(gl, _TaskGreenlet):
            raise RuntimeError(
                    '"greentulip.yield_from" was supposed to be called from a '
                    '"greentulip.task" or a subsequent coroutine')

    task = gl.task

    if not isinstance(future, futures.Future):
        raise RuntimeError(
                'greenlet.yield_from was supposed to receive only Futures, '
                'got {!r} in task {!r}'.format(future, task))

    else:
        future.add_done_callback(task._wakeup)
        task._fut_waiter = future

        # task cancellation has been delayed.
        if task._must_cancel:
            talk._fut_waiter.cancel()

    return gl.parent.switch(_YIELDED)


def task(func):
    """A decorator, allows use of ``yield_from`` in the decorated or
    subsequent coroutines.
    """

    coro = tulip.coroutine(func)

    def task_wrapper(*args, **kwds):
        return GreenTask(coro(*args, **kwds))

    return task_wrapper


class _YIELDED:
    """Marker, don't use it"""