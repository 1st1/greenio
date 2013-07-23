##
# Copyright (c) 2013 Yury Selivanov
# License: Apache 2.0
##
"""Greensocket (non-blocking) for Tulip.

Use ``greentulip.socket`` in the same way as you would use stdlib's
``socket.socket`` in ``greentulip.task`` tasks or coroutines invoked
from them.
"""
import tulip
from socket import error, SOCK_STREAM
from socket import socket as std_socket

from . import yield_from


class socket:

    def __init__(self, *args, _from_sock=None, **kwargs):
        if _from_sock:
            self._sock = _from_sock
        else:
            self._sock = std_socket(*args, **kwargs)
        self._sock.setblocking(False)
        self._loop = tulip.get_event_loop()

    @classmethod
    def from_socket(cls, sock):
        return cls(_from_sock=sock)

    @property
    def family(self):
        return self._sock.family

    @property
    def type(self):
        return self._sock.type

    @property
    def proto(self):
        return self._sock.proto

    def _proxy(attr):
        def proxy(self, *args, **kwargs):
            meth = getattr(self._sock, attr)
            return meth(*args, **kwargs)

        proxy.__name__ = attr
        proxy.__qualname__ = attr
        proxy.__doc__ = getattr(getattr(std_socket, attr), '__doc__', None)
        return proxy

    def _copydoc(func):
        func.__doc__ = getattr(
            getattr(std_socket, func.__name__), '__doc__', None)
        return func

    @_copydoc
    def setblocking(self, flag):
        if flag:
            raise error('greentulip.socket does not support blocking mode')

    @_copydoc
    def recv(self, nbytes):
        fut = self._loop.sock_recv(self._sock, nbytes)
        yield_from(fut)
        return fut.result()

    @_copydoc
    def connect(self, addr):
        fut = self._loop.sock_connect(self._sock, addr)
        yield_from(fut)
        return fut.result()

    @_copydoc
    def sendall(self, data, flags=0):
        assert not flags
        fut = self._loop.sock_sendall(self._sock, data)
        yield_from(fut)
        return fut.result()

    @_copydoc
    def send(self, data, flags=0):
        self.sendall(data, flags)
        return len(data)

    @_copydoc
    def accept(self):
        fut = self._loop.sock_accept(self._sock)
        yield_from(fut)
        sock, addr = fut.result()
        return self.__class__.from_socket(sock), addr

    @_copydoc
    def makefile(self, *args, **kwargs):
        if args:
            if args[0] == 'rb':
                return ReadFile(self._loop, self._sock)
            elif args[0] == 'wb':
                return WriteFile(self._loop, self._sock)
        raise NotImplementedError

    bind = _proxy('bind')
    listen = _proxy('listen')
    getsockname = _proxy('getsockname')
    getpeername = _proxy('getpeername')
    gettimeout = _proxy('gettimeout')
    getsockopt = _proxy('getsockopt')
    setsockopt = _proxy('setsockopt')
    fileno = _proxy('fileno')
    detach = _proxy('detach')
    close = _proxy('close')
    shutdown = _proxy('shutdown')

    del _copydoc, _proxy


class ReadFile:

    def __init__(self, loop, sock):
        self._loop = loop
        self._sock = sock
        self._buf = bytearray()

    def read(self, size):
        while 1:
            if size <= len(self._buf):
                data = self._buf[:size]
                del self._buf[:size]
                return data

            fut = self._loop.sock_recv(self._sock, size - len(self._buf))
            yield_from(fut)
            res = fut.result()
            self._buf.extend(res)

    def close(self):
        pass


class WriteFile:

    def __init__(self, loop, sock):
        self._loop = loop
        self._sock = sock
        self._buf = bytearray()

    def write(self, data):
        fut = self._loop.sock_sendall(self._sock, data)
        yield_from(fut)
        return fut.result()

    def flush(self):
        pass

    def close(self):
        pass


def create_connection(address: tuple, timeout=None):
    loop = tulip.get_event_loop()
    host, port = address

    rslt = yield_from(
        loop.getaddrinfo(host, port, family=0, type=SOCK_STREAM))

    for res in rslt:
        af, socktype, proto, canonname, sa = res
        sock = None

        try:
            sock = socket(af, socktype, proto)
            sock.connect(sa)
            return sock
        except ConnectionError:
            if sock:
                sock.close()

    raise error('unable to connect to {!r}'.format(address))
