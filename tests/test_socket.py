##
# Copyright (c) 2013 Yury Selivanov
# License: Apache 2.0
##


import asyncio
import unittest

import greenio
import greenio.socket as greensocket


class SocketTests(unittest.TestCase):

    def setUp(self):
        asyncio.set_event_loop_policy(greenio.GreenEventLoopPolicy())
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def tearDown(self):
        self.loop.close()
        asyncio.set_event_loop_policy(None)

    def test_socket_wrong_event_loop(self):
        loop = asyncio.DefaultEventLoopPolicy().new_event_loop()
        self.addCleanup(loop.close)
        asyncio.set_event_loop(loop)
        self.assertRaises(AssertionError, greensocket.socket)

    def test_socket_docs(self):
        self.assertIn('accept connections', greensocket.socket.listen.__doc__)
        self.assertIn('Receive', greensocket.socket.recv.__doc__)

    def test_socket_setblocking(self):
        sock = greensocket.socket()
        self.assertEquals(sock.gettimeout(), 0)
        with self.assertRaisesRegex(
                greensocket.error, 'does not support blocking mode'):
            sock.setblocking(True)
        sock.close()

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
            greenio.task(server)(greensocket.socket))
        thread.join(1)
        self.assertEqual(check, 1)

        addr = None
        ev.clear()
        thread = threading.Thread(target=server, args=(std_socket.socket,))
        thread.setDaemon(True)
        thread.start()
        self.loop.run_until_complete(
            greenio.task(client)(greensocket.socket))
        thread.join(1)
        self.assertEqual(check, 2)

    def test_files_socket_echo(self):
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
            greenio.task(server)(greensocket.socket))
        thread.join(1)
        self.assertEqual(check, 1)
