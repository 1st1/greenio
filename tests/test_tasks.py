##
# Copyright (c) 2013 Yury Selivanov
# License: Apache 2.0
##


import greentulip
import tulip
import unittest


class TaskTests(unittest.TestCase):
    def setUp(self):
        tulip.set_event_loop_policy(greentulip.GreenEventLoopPolicy())
        self.loop = tulip.new_event_loop()
        tulip.set_event_loop(self.loop)

    def tearDown(self):
        self.loop.close()
        tulip.set_event_loop_policy(None)

    def test_task_yield_from_plain(self):
        @tulip.task
        def bar():
            yield
            return 30

        @tulip.coroutine
        def foo():
            bar_result = greentulip.yield_from(bar())
            return bar_result + 12

        @greentulip.task
        def test():
            return (yield from foo())

        fut = test()
        self.loop.run_until_complete(fut)

        self.assertEqual(fut.result(), 42)

    def test_task_yield_from_exception_propagation(self):
        CHK = 0

        @tulip.task
        def bar():
            yield
            yield
            1/0

        @greentulip.task
        def foo():
            greentulip.yield_from(bar())

        @tulip.task
        def test():
            try:
                return (yield from foo())
            except ZeroDivisionError:
                nonlocal CHK
                CHK += 1

        fut = test()
        self.loop.run_until_complete(fut)
        self.assertEqual(CHK, 1)

    def test_task_yield_from_nonfuture(self):
        @tulip.coroutine
        def bar():
            yield

        @greentulip.task
        def foo():
            with self.assertRaisesRegex(
                    RuntimeError,
                    'greenlet.yield_from was supposed to receive '
                    'only Futures'):
                greentulip.yield_from(bar())

        fut = foo()
        self.loop.run_until_complete(fut)

    def test_task_yield_from_invalid(self):
        @tulip.coroutine
        def bar():
            yield

        @tulip.task
        def foo():
            with self.assertRaisesRegex(
                    RuntimeError,
                    '"greentulip.yield_from" was supposed to be called'):
                greentulip.yield_from(bar())

        fut = foo()
        self.loop.run_until_complete(fut)
