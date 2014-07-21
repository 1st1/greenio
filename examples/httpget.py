##
# Copyright (c) 2013 Yury Selivanov
# License: Apache 2.0
##


import greenio
import asyncio


@asyncio.coroutine
def sleeper():
    while True:
        yield from asyncio.sleep(0.05)
        print('.')


@greenio.task
def get():
    from greenio import socket

    sock = socket.create_connection(('python.org', 80))
    print('connected', sock._sock)
    sock.sendall(b'GET / HTTP/1.0\r\n\r\n')
    print('sent')
    print('rcvd', sock.recv(1024))
    sock.close()


@asyncio.coroutine
def run():
    yield from asyncio.wait(
        [get(), sleeper()], return_when=asyncio.FIRST_COMPLETED)


asyncio.set_event_loop_policy(greenio.GreenEventLoopPolicy())
loop = asyncio.get_event_loop()
loop.run_until_complete(run())
loop.close()
