# -*- coding: utf-8 -*-

import time
import pytest
import pymssql


@pytest.mark.timeout(120)
@pytest.mark.xfail(strict=False)
@pytest.mark.parametrize('to', range(2,20,2))
def test_remote_connect_timeout(to):

    t = time.time()
    try:
        pymssql.connect(server="www.google.com", port=81, user='username', password='password',
                            login_timeout=to)
    except pymssql.OperationalError:
        pass
    t = time.time() - t
    print('remote: requested {} -> {} actual timeout'.format(to, t))
    assert t == pytest.approx(to, 5), "{} != {}".format(t, to)



import threading
import sys
if sys.version_info[0] == 2:
    import SocketServer as SS
else:
    import socketserver as SS

gdt = 0
gconnections = 0

class ThreadedTCPRequestHandler(SS.BaseRequestHandler):

    def handle(self):
        global gdt
        global gconnections
        gconnections += 1
        t = time.time()
        data = 1
        while data:
            data = self.request.recv(1024)
        gdt = time.time() - t


class ThreadedTCPServer(SS.ThreadingMixIn, SS.TCPServer):
    request_queue_size=0
    pass


@pytest.mark.timeout(120)
@pytest.mark.xfail(strict=False)
@pytest.mark.parametrize('to', range(2,20,2))
def test_local_connect_timeout(to):

    global gdt
    global gconnections

    HOST, PORT = "localhost", 0
    server = ThreadedTCPServer((HOST, PORT), ThreadedTCPRequestHandler)
    ip, port = server.server_address
    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.daemon = True
    server_thread.start()
    #print("Server loop running in thread:", server_thread.name)

    gconnections = 0
    t = time.time()
    try:
        pymssql.connect(server=HOST, port=port, user='username', password='password',
                        login_timeout=to)
    except pymssql.OperationalError:
        pass
    t = time.time() - t
    print('local: requested {} -> {} actual timeout ({} server side, n={})'.format(to, t, gdt, gconnections))
    assert t == pytest.approx(to, 5), "{} != {}".format(t, to)

    server.shutdown()
    server.server_close()
