##
# Copyright (c) 2013 Yury Selivanov
# License: Apache 2.0
##


import greentulip
import asyncio


@asyncio.coroutine
def bar():
    yield
    return 30


@asyncio.coroutine
def foo():
    bar_result = greentulip.yield_from(asyncio.Task(bar()))
    return bar_result + 12


@greentulip.task
def test():
    print((yield from foo()))


asyncio.set_event_loop_policy(greentulip.GreenEventLoopPolicy())
asyncio.get_event_loop().run_until_complete(test())
