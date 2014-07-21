##
# Copyright (c) 2013 Yury Selivanov
# License: Apache 2.0
##


from trollius import From, Return
from trollius.test_utils import TestCase
import greenio
import trollius
try:
    import asyncio
except ImportError:
    asyncio = None


class TrolliusTaskTests(TestCase):
    def setUp(self):
        policy = greenio.GreenTrolliusEventLoopPolicy()
        trollius.set_event_loop_policy(policy)
        if asyncio is not None:
            asyncio.set_event_loop_policy(policy)
        self.loop = trollius.new_event_loop()
        policy.set_event_loop(self.loop)

    def tearDown(self):
        self.loop.close()
        trollius.set_event_loop_policy(None)

    def test_task_yield_from_plain(self):
        @trollius.coroutine
        def bar():
            yield From(None)
            raise Return(30)

        @trollius.coroutine
        def foo():
            bar_result = greenio.yield_from(bar())
            return bar_result + 12

        @greenio.task
        def test():
            res = yield From(foo())
            raise Return(res)

        fut = test()
        self.loop.run_until_complete(fut)

        self.assertEqual(fut.result(), 42)

    def test_task_yield_from_exception_propagation(self):
        non_local = {'CHK': 0}

        @trollius.coroutine
        def bar():
            yield From(None)
            yield From(None)
            1/0

        @greenio.task
        def foo():
            greenio.yield_from(bar())

        @trollius.coroutine
        def test():
            try:
                res = yield From(foo())
                raise Return(res)
            except ZeroDivisionError:
                non_local['CHK'] += 1

        self.loop.run_until_complete(test())
        self.assertEqual(non_local['CHK'], 1)

    def test_task_yield_from_coroutine(self):
        @trollius.coroutine
        def bar():
            yield From(None)
            raise Return(5)

        @greenio.task
        def foo():
            return greenio.yield_from(bar())

        fut = foo()
        self.loop.run_until_complete(fut)
        self.assertEqual(fut.result(), 5)

    def test_task_yield_from_invalid(self):
        def bar():
            pass

        err_msg = (r"^greenlet.yield_from was supposed to receive "
                   r"only Futures, got .* in task .*$")

        @trollius.coroutine
        def foo():
            with self.assertRaisesRegex(RuntimeError, err_msg):
                greenio.yield_from(bar)

        self.loop.run_until_complete(foo())
