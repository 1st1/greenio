##
# Copyright (c) 2013 Yury Selivanov
# License: Apache 2.0
##


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

    def setblocking(flag):
        assert not flag, 'greenlet.socket does not support blocking mode'

    def recv(self, nbytes):
        fut = tulip.get_event_loop().sock_recv(self._sock, nbytes)
        return yield_from(fut)

    def connect(self, addr):
        fut = tulip.get_event_loop().sock_connect(self._sock, addr)
        return yield_from(fut)

    def sendall(self, data, flags=0):
        assert not flags
        fut = tulip.get_event_loop().sock_sendall(self._sock, data)
        return yield_from(fut)

    def send(self, data, flags=0):
        assert not flags
        fut = tulip.get_event_loop().sock_sendall(self._sock, data)
        yield_from(fut)
        return len(data)

    def accept(self):
        fut = tulip.get_event_loop().sock_accept(self._sock)
        return yield_from(fut)

    def close(self):
        return self._sock.close()


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
