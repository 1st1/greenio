##
# Copyright (c) 2013 Yury Selivanov
# License: Apache 2.0
##
import greentulip
import greentulip.socket as greensocket

import tulip
import unittest


class SocketTests(unittest.TestCase):

    def setUp(self):
        tulip.set_event_loop_policy(greentulip.GreenEventLoopPolicy())
        self.loop = tulip.new_event_loop()
        tulip.set_event_loop(self.loop)

    def tearDown(self):
        self.loop.close()
        tulip.set_event_loop_policy(None)

    def test_socket_docs(self):
        self.assertIn('accept connections', greensocket.socket.listen.__doc__)
        self.assertIn('Receive', greensocket.socket.recv.__doc__)

    def test_socket_setblocking(self):
        sock = greensocket.socket()
        self.assertEquals(sock.gettimeout(), 0)
        with self.assertRaisesRegex(
                greensocket.error, 'does not support blocking mode'):
            sock.setblocking(True)

    def test_socket_echo(self):
        import socket as std_socket
        import threading
        import time

        check = 0
        ev = threading.Event()

        def server(sock_factory):
            socket = sock_factory()
            socket.bind(('127.0.0.1', 0))

            assert socket.fileno() is not None

            nonlocal addr
            addr = socket.getsockname()
            socket.listen(1)

            ev.set()

            sock, client_addrs = socket.accept()
            assert isinstance(sock, sock_factory)

            data = b''
            while not data.endswith(b'\r'):
                data += sock.recv(1024)

            sock.sendall(data)

            ev.wait()
            ev.clear()

            sock.close()
            socket.close()

        def client(sock_factory):
            ev.wait()
            ev.clear()
            time.sleep(0.1)

            assert addr
            sock = sock_factory()
            sock.connect(addr)

            data = b'hello greenlets\r'
            sock.sendall(data)

            rep = b''
            while not rep.endswith(b'\r'):
                rep += sock.recv(1024)

            self.assertEqual(data, rep)
            ev.set()

            nonlocal check
            check += 1

            sock.close()

        addr = None
        ev.clear()
        thread = threading.Thread(target=client, args=(std_socket.socket,))
        thread.setDaemon(True)
        thread.start()
        self.loop.run_until_complete(
            greentulip.task(server)(greensocket.socket))
        thread.join(1)
        self.assertEqual(check, 1)

        addr = None
        ev.clear()
        thread = threading.Thread(target=server, args=(std_socket.socket,))
        thread.setDaemon(True)
        thread.start()
        self.loop.run_until_complete(
            greentulip.task(client)(greensocket.socket))
        thread.join(1)
        self.assertEqual(check, 2)
