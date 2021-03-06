##
# Copyright (c) 2013 Yury Selivanov
# License: Apache 2.0
##


try:
    import asyncio
except ImportError:
    asyncio = None
try:
    import trollius
except ImportError:
    trollius = None
if asyncio is None and trollius is None:
    raise ImportError("asyncio and trollius modules are missing")

try:
    from trollius.test_utils import TestCase
except ImportError:
    from unittest import TestCase

import greenio
import greenio.socket as greensocket

import socket as std_socket


class SocketMixin(object):
    asyncio = None
    event_loop_policy = greenio.GreenEventLoopPolicy

    def setUp(self):
        policy = self.event_loop_policy()
        self.asyncio.set_event_loop_policy(policy)
        self.loop = policy.new_event_loop()
        policy.set_event_loop(self.loop)

    def tearDown(self):
        self.loop.close()
        self.asyncio.set_event_loop_policy(None)

    def test_socket_wrong_event_loop(self):
        loop = self.asyncio.DefaultEventLoopPolicy().new_event_loop()
        self.addCleanup(loop.close)
        self.asyncio.set_event_loop(loop)
        self.assertRaises(AssertionError, greensocket.socket)

    def test_socket_docs(self):
        self.assertIn('accept connections', greensocket.socket.listen.__doc__)
        # On Python 2.7, socket.recv() has no documentation
        if std_socket.socket.recv.__doc__:
            self.assertIn('Receive', greensocket.socket.recv.__doc__)

    def test_socket_setblocking(self):
        sock = greensocket.socket()
        self.assertEquals(sock.gettimeout(), 0)
        with self.assertRaisesRegex(
                greensocket.error, 'does not support blocking mode'):
            sock.setblocking(True)
        sock.close()

    def test_socket_echo(self):
        import threading
        import time

        non_local = {'addr': None, 'check': 0}
        ev = threading.Event()

        def server(sock_factory):
            socket = sock_factory()
            socket.bind(('127.0.0.1', 0))

            assert socket.fileno() is not None

            non_local['addr'] = socket.getsockname()
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

            sock = sock_factory()
            sock.connect(non_local['addr'])

            data = b'hello greenlets\r'
            sock.sendall(data)

            rep = b''
            while not rep.endswith(b'\r'):
                rep += sock.recv(1024)

            self.assertEqual(data, rep)
            ev.set()

            non_local['check'] += 1

            sock.close()

        ev.clear()
        thread = threading.Thread(target=client, args=(std_socket.socket,))
        thread.setDaemon(True)
        thread.start()
        self.loop.run_until_complete(
            greenio.task(server)(greensocket.socket))
        thread.join(1)
        self.assertEqual(non_local['check'], 1)

        non_local['addr'] = None
        ev.clear()
        thread = threading.Thread(target=server, args=(std_socket.socket,))
        thread.setDaemon(True)
        thread.start()
        self.loop.run_until_complete(
            greenio.task(client)(greensocket.socket))
        thread.join(1)
        self.assertEqual(non_local['check'], 2)

    def test_files_socket_echo(self):
        import threading
        import time

        non_local = {'check': 0, 'addr': None}
        ev = threading.Event()

        def server(sock_factory):
            socket = sock_factory()
            socket.bind(('127.0.0.1', 0))

            assert socket.fileno() is not None

            non_local['addr'] = socket.getsockname()
            socket.listen(1)

            ev.set()

            sock, client_addrs = socket.accept()
            assert isinstance(sock, sock_factory)

            rfile = sock.makefile('rb')
            data = rfile.read(1024)
            while not data.endswith(b'\r'):
                data += rfile.read(1024)

            wfile = sock.makefile('wb')
            wfile.write(data)

            ev.wait()
            ev.clear()

            sock.close()
            socket.close()

        def client(sock_factory):
            ev.wait()
            ev.clear()
            time.sleep(0.1)

            sock = sock_factory()
            sock.connect(non_local['addr'])

            data = b'hello greenlets\r'
            sock.sendall(data)

            rep = b''
            while not rep.endswith(b'\r'):
                rep += sock.recv(1024)

            self.assertEqual(data, rep)
            ev.set()

            non_local['check'] += 1

            sock.close()

        ev.clear()
        thread = threading.Thread(target=client, args=(std_socket.socket,))
        thread.setDaemon(True)
        thread.start()
        self.loop.run_until_complete(
            greenio.task(server)(greensocket.socket))
        thread.join(1)
        self.assertEqual(non_local['check'], 1)

if asyncio is not None:
    class SocketTests(SocketMixin, TestCase):
        asyncio = asyncio
        event_loop_policy = greenio.GreenEventLoopPolicy

if trollius is not None:
    class TrolliusSocketTests(SocketMixin, TestCase):
        asyncio = trollius
        event_loop_policy = greenio.GreenTrolliusEventLoopPolicy

        def setUp(self):
            super(TrolliusSocketTests, self).setUp()
            if asyncio is not None:
                policy = trollius.get_event_loop_policy()
                asyncio.set_event_loop_policy(policy)
