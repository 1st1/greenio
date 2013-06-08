##
# Copyright (c) 2013 Yury Selivanov
# License: Apache 2.0
##


import greentulip
import tulip


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
    print((yield from foo()))


tulip.set_event_loop_policy(greentulip.GreenEventLoopPolicy())
tulip.get_event_loop().run_until_complete(test())
