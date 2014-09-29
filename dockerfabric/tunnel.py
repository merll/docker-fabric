# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import select
import socket
import errno

from fabric.network import needs_host
from fabric.state import connections, env
from fabric.thread_handling import ThreadHandler


class LocalTunnels(dict):
    """
    Cache for local tunnels to the remote machine.
    """
    def __getitem__(self, item):
        """
        :param item: Tuple of remote host, remote port, local port number, and local bind address.
        :type item: tuple
        :return: Local tunnel
        :rtype: LocalTunnel
        """
        remote_host, remote_port, bind_port, bind_host = item
        key = remote_host, remote_port
        tun = self.get(key)
        if not tun:
            tun = LocalTunnel(remote_port, remote_host, bind_port, bind_host)
            tun.connect()
            self[key] = tun
        return tun


local_tunnels = LocalTunnels()


def _forwarder(chan, sock):
    # Bidirectionally forward data between a socket and a Paramiko channel.
    try:
        while True:
            r, w, x = select.select([sock, chan], [], [], 1)
            if sock in r:
                data = sock.recv(1024)
                if len(data) == 0:
                    break
                chan.sendall(data)
            if chan in r:
                data = chan.recv(1024)
                if len(data) == 0:
                    break
                sock.sendall(data)
    except socket.error as e:
        #Sockets return bad file descriptor if closed.
        #Maybe there is a cleaner way of doing this?
        if e.errno not in (socket.EBADF, errno.ECONNRESET):
            raise
    except select.error as e:
        if e[0] != socket.EBADF:
            raise

    try:
        chan.close()
    except socket.error:
        pass

    try:
        sock.close()
    except socket.error:
        pass


class LocalTunnel(object):
    """
    Posted as PR #939 of Fabric: https://github.com/fabric/fabric/pull/939

    Forward a local port to a given host and port on the remote side.

    For example, you can use this to run local commands which connect to a
    database which is only bound to localhost on server:

    # Map localhost:6379 on the client to localhost:6379 on the server,
    # so that the local 'redis-cli' program ends up speaking to the remote
    # redis-server.
    with local_tunnel(6379):
    local("redis-cli -i")

    ``local_tunnel`` accepts up to three arguments:

    * ``remote_port`` (mandatory) is the remote port to connect to.
    * ``remote_host`` (optional) is the remote host to connect to; the
      default is ``localhost``.
    * ``bind_port`` (optional) is the local port to bind; the default
      is ``remote_port``.
    * ``bind_host`` (optional) is the local address (DNS name or
      IP address) on which to bind; the default is ``localhost``.
    """
    def __init__(self, remote_port, remote_host=None, bind_port=None, bind_host=None):
        self.remote_port = remote_port
        self.remote_host = remote_host or 'localhost'
        self.bind_port = bind_port or remote_port
        self.bind_host = bind_host or 'localhost'
        self.sockets = []
        self.channels = []
        self.threads = []
        self.listening_socket = None
        self.listening_thread = None

    @needs_host
    def connect(self):
        def listener_thread_main(thead_sock, callback, *a, **kw):
            try:
                while True:
                    selsockets = select.select([thead_sock], [], [], 1)
                    if thead_sock in selsockets[0]:
                        callback(thead_sock, *a, **kw)
            except socket.error as e:
                #Sockets return bad file descriptor if closed.
                #Maybe there is a cleaner way of doing this?
                if e.errno != socket.EBADF:
                    raise
            except select.error as e:
                if e[0] != socket.EBADF:
                    raise

        listening_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listening_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listening_socket.bind((self.bind_host, self.bind_port))
        listening_socket.listen(1)

        def accept(listen_sock, transport, remote_addr):
            accept_sock, local_peer = listen_sock.accept()
            channel = transport.open_channel('direct-tcpip',
                                             remote_addr,
                                             local_peer)

            if channel is None:
                raise Exception('Incoming request to %s:%d was rejected by the SSH server.' % remote_addr)

            handler = ThreadHandler('fwd', _forwarder, channel, accept_sock)

            self.sockets.append(accept_sock)
            self.channels.append(channel)
            self.threads.append(handler)

        self.sockets = []
        self.channels = []
        self.threads = []
        self.listening_socket = listening_socket
        self.listening_thread = ThreadHandler('local_bind', listener_thread_main,
                                               listening_socket, accept,
                                               connections[env.host_string].get_transport(),
                                               (self.remote_host, self.remote_port))

    def close(self):
        for sock, chan, th in zip(self.sockets, self.channels, self.threads):
            sock.close()
            if not chan.closed:
                chan.close()
            th.thread.join()
            th.raise_if_needed()

        self.listening_socket.close()
        self.listening_thread.thread.join()
        self.listening_thread.raise_if_needed()
