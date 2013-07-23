##
# Copyright (c) 2008-2012 Sprymix Inc.
# License: Apache 2.0
##


"""A non-blocking adapter for py-postgresql library.
WARNING: This is just an experiment; use in production is not recommended.
"""


import postgresql
from postgresql.python import socket as pg_socket
from postgresql.driver import pq3

from greentulip import socket as greensocket


class SocketConnector:
    def create_socket_factory(self, **params):
        params['socket_extra'] = {'async': self.async}
        return SocketFactory(**params)

    def __init__(self, async=False):
        self.async = async


class IPConnector(pq3.IPConnector, SocketConnector):
    def __init__(self, *args, async=False, **kw):
        pq3.IPConnector.__init__(self, *args, **kw)
        SocketConnector.__init__(self, async=async)


class IP4(IPConnector, pq3.IP4):
    pass


class IP6(IPConnector, pq3.IP6):
    pass


class Host(SocketConnector, pq3.Host):
    def __init__(self, *args, async=False, **kw):
        pq3.Host.__init__(self, *args, **kw)
        SocketConnector.__init__(self, async=async)


class Unix(SocketConnector, pq3.Unix):
    def __init__(self, unix=None, async=False, **kw):
        pq3.Unix.__init__(self, unix=unix, **kw)
        SocketConnector.__init__(self, async=async)


class SocketFactory(pg_socket.SocketFactory):
    def __init__(self, *args, socket_extra=None, **kw):
        super().__init__(*args, **kw)
        self.async = (socket_extra.get('async', False)
                      if socket_extra else False)

    def __call__(self, timeout=None):
        if self.async:
            s = greensocket.socket(*self.socket_create)
            s.connect(self.socket_connect)
            return s
        else:
            return super().__call__(timeout)


class Driver(pq3.Driver):
    def ip4(self, **kw):
        return IP4(driver=self, **kw)

    def ip6(self, **kw):
        return IP6(driver=self, **kw)

    def host(self, **kw):
        return Host(driver=self, **kw)

    def unix(self, **kw):
        return Unix(driver=self, **kw)


driver = Driver()


def connector_factory(iri, async=False):
    params = postgresql.iri.parse(iri)
    settings = params.setdefault('settings', {})
    settings['standard_conforming_strings'] = 'on'
    params['async'] = async
    return driver.fit(**params)


if __name__ == '__main__':
    import greentulip
    import time
    import tulip

    @tulip.task
    def sleeper():
        # show that we're not blocked
        while True:
            yield from tulip.sleep(0.4)
            print('.')

    @greentulip.task
    def db():
        connection = connector_factory(
            'pq://postgres@localhost:5432', async=True)()
        connection.connect()

        try:
            print('>> sleeping')
            st = time.monotonic()
            connection.execute('SELECT pg_sleep(2)')
            en = time.monotonic() - st
            assert en >= 2
            print('<< sleeping {:.3f}s'.format(en))

            ps = connection.prepare('SELECT 42')
            print('"SELECT 42" -> {!r}'.format(ps()))
        finally:
            connection.close()

    @tulip.task
    def run():
        yield from tulip.wait(
            [db(), sleeper()], return_when=tulip.FIRST_COMPLETED)

    tulip.set_event_loop_policy(greentulip.GreenEventLoopPolicy())
    tulip.get_event_loop().run_until_complete(run())
