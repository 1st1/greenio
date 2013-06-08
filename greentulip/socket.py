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

from socket import *
from socket import socket as std_socket

from . import yield_from


class socket:
    def __init__(self, *args, _from_sock=None, **kwargs):
        if _from_sock:
            self._sock = _from_sock
        else:
            self._sock = std_socket(*args, **kwargs)
        self._sock.setblocking(False)

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
        func.__doc__ = getattr(getattr(std_socket, func.__name__), '__doc__', None)
        return func

    @_copydoc
    def setblocking(self, flag):
        if flag:
            raise error('greentulip.socket does not support blocking mode')

    @_copydoc
    def recv(self, nbytes):
        fut = tulip.get_event_loop().sock_recv(self._sock, nbytes)
        yield_from(fut)
        return fut.result()

    @_copydoc
    def connect(self, addr):
        fut = tulip.get_event_loop().sock_connect(self._sock, addr)
        yield_from(fut)
        return fut.result()

    @_copydoc
    def sendall(self, data, flags=0):
        assert not flags
        fut = tulip.get_event_loop().sock_sendall(self._sock, data)
        yield_from(fut)
        return fut.result()

    @_copydoc
    def send(self, data, flags=0):
        self.sendall(data, flags)
        return len(data)

    @_copydoc
    def accept(self):
        fut = tulip.get_event_loop().sock_accept(self._sock)
        yield_from(fut)
        sock, addr = fut.result()
        return self.__class__.from_socket(sock), addr

    @_copydoc
    def makefile(self, *args, **kwargs):
        raise NotImplementedError

    bind        = _proxy('bind')
    listen      = _proxy('listen')
    getsockname = _proxy('getsockname')
    getpeername = _proxy('getpeername')
    gettimeout  = _proxy('gettimeout')
    getsockopt  = _proxy('getsockopt')
    setsockopt  = _proxy('setsockopt')
    fileno      = _proxy('fileno')
    detach      = _proxy('detach')
    close       = _proxy('close')
    shutdown    = _proxy('shutdown')

    del _copydoc, _proxy


def create_connection(address:tuple, timeout=None):
    loop = tulip.get_event_loop()
    host, port = address

    rslt = yield_from(loop.getaddrinfo(host, port, family=0, type=SOCK_STREAM))

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
