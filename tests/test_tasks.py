##
# Copyright (c) 2013 Yury Selivanov
# License: Apache 2.0
##


import greenio
import asyncio
import unittest


class TaskTests(unittest.TestCase):
    def setUp(self):
        asyncio.set_event_loop_policy(greenio.GreenEventLoopPolicy())
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def tearDown(self):
        self.loop.close()
        asyncio.set_event_loop_policy(None)

    def test_task_yield_from_plain(self):
        @asyncio.coroutine
        def bar():
            yield
            return 30

        @asyncio.coroutine
        def foo():
            bar_result = greenio.yield_from(asyncio.Task(bar()))
            return bar_result + 12

        @greenio.task
        def test():
            return (yield from foo())

        fut = test()
        self.loop.run_until_complete(fut)

        self.assertEqual(fut.result(), 42)

    def test_task_yield_from_exception_propagation(self):
        CHK = 0

        @asyncio.coroutine
        def bar():
            yield
            yield
            1/0

        @greenio.task
        def foo():
            greenio.yield_from(asyncio.Task(bar()))

        @asyncio.coroutine
        def test():
            try:
                return (yield from foo())
            except ZeroDivisionError:
                nonlocal CHK
                CHK += 1

        self.loop.run_until_complete(test())
        self.assertEqual(CHK, 1)

    def test_task_yield_from_nonfuture(self):
        @asyncio.coroutine
        def bar():
            yield

        @greenio.task
        def foo():
            with self.assertRaisesRegex(
                    RuntimeError,
                    'greenlet.yield_from was supposed to receive '
                    'only Futures'):
                greenio.yield_from(bar())

        fut = foo()
        self.loop.run_until_complete(fut)

    def test_task_yield_from_invalid(self):
        @asyncio.coroutine
        def bar():
            yield

        @asyncio.coroutine
        def foo():
            with self.assertRaisesRegex(
                    RuntimeError,
                    '"greenio.yield_from" was supposed to be called'):
                greenio.yield_from(bar())

        self.loop.run_until_complete(foo())
