# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import select
import socket
import errno

from fabric.network import needs_host
from fabric.state import connections, env
from fabric.thread_handling import ThreadHandler

from .base import ConnectionDict, get_local_port


class LocalTunnels(ConnectionDict):
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
        def _connect_local_tunnel():
            bind_port = get_local_port(init_bind_port)
            tun = LocalTunnel(remote_port, remote_host, bind_port, bind_host)
            tun.connect()
            return tun

        remote_host, remote_port, bind_host, init_bind_port = item
        key = remote_host, remote_port
        return self.get(key, _connect_local_tunnel)


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
    Adapted from PR #939 of Fabric: https://github.com/fabric/fabric/pull/939

    Forward a local port to a given host and port on the remote side.

    :param remote_port: Remote port to forward connections to.
    :type remote_port: int
    :param remote_host: Host to connect to. Optional, default is ``localhost``.
    :type remote_host: unicode
    :param bind_port: Local port to bind to. Optional, default is same as ``remote_port``.
    :type bind_port: int
    :param bind_host: Local address to bind to. Optional, default is ``localhost``.
    """
    def __init__(self, remote_port, remote_host=None, bind_port=None, bind_host=None, remote_cmd=None):
        self.remote_port = remote_port
        self.remote_host = remote_host or 'localhost'
        self.bind_port = bind_port or remote_port
        self.bind_host = bind_host or 'localhost'
        self.remote_cmd = remote_cmd
        self.sockets = []
        self.channels = []
        self.threads = []
        self.listening_socket = None
        self.listening_thread = None

    def get_channel(self, transport, remote_addr, local_peer):
        channel = transport.open_channel('direct-tcpip', remote_addr, local_peer)
        if channel is None:
            raise Exception('Incoming request to %s:%d was rejected by the SSH server.' % remote_addr)
        return channel

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
            channel = self.get_channel(transport, remote_addr, local_peer)

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
