"""
Test interoperability between asyncio and trollius. Trollius event loop should
support asyncio coroutines.
"""

import asyncio
import greenio
import trollius
import unittest
from trollius import From, Return
from trollius.test_utils import TestCase


class TrolliusEventLoopTests(TestCase):
    def setUp(self):
        policy = greenio.GreenTrolliusEventLoopPolicy()
        asyncio.set_event_loop_policy(policy)
        trollius.set_event_loop_policy(policy)
        self.loop = trollius.new_event_loop()
        policy.set_event_loop(self.loop)

    def tearDown(self):
        self.loop.close()
        asyncio.set_event_loop_policy(None)

    def test_trollius_coroutine(self):
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

    def test_asyncio_coroutine(self):
        @asyncio.coroutine
        def bar():
            yield from []
            return 30

        @asyncio.coroutine
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


if __name__ == '__main__':
    unittest.main()
