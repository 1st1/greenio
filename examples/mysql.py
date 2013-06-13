"""PyMySQL example"""
import tulip
import socket
from pymysql import connections
from greentulip import socket as greensocket


class GreenConnection(connections.Connection):

    def _connect(self):
        try:
            if self.unix_socket:
                raise NotImplementedError()
            else:
                sock = greensocket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect((self.host, self.port))
                self.host_info = "socket %s:%d" % (self.host, self.port)
            if self.no_delay:
                sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            self.socket = sock
            self.rfile = self.socket.makefile("rb")
            self.wfile = self.socket.makefile("wb")
            self._get_server_information()
            self._request_authentication()
            self._send_autocommit_mode()
        except socket.error as e:
            raise Exception(
                2003, "Can't connect to MySQL server on %r (%s)" % (
                    self.host, e.args[0]))


if __name__ == '__main__':
    import greentulip
    import time
    import tulip

    @tulip.task
    def sleeper():
        # show that we're not blocked
        while True:
            yield from tulip.sleep(0.2)
            print('.')

    @greentulip.task
    def db():
        conn = GreenConnection(host='localhost')

        try:
            with conn as cur:
                print('>> sleeping')
                st = time.monotonic()
                cur.execute('SELECT SLEEP(2)')
                en = time.monotonic() - st
                assert en >= 2
                print('<< sleeping {:.3f}s'.format(en))

                cur.execute('SELECT 42')
                print('"SELECT 42" -> {!r}'.format(cur.fetchone()))

                print('>> sleeping')
                st = time.monotonic()
                cur.execute('SELECT SLEEP(1)')
                en = time.monotonic() - st
                assert en >= 1
                print('<< sleeping {:.3f}s'.format(en))
        finally:
            conn.close()

    @tulip.task
    def run():
        yield from tulip.wait([db(), sleeper()],
                              return_when=tulip.FIRST_COMPLETED)

    tulip.set_event_loop_policy(greentulip.GreenEventLoopPolicy())
    tulip.get_event_loop().run_until_complete(run())
