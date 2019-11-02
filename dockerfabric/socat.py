# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import socket
import errno
import time
from threading import Event

from fabric.tunnels import TunnelManager, Tunnel
from invoke import ThreadException

from .tunnel import LocalTunnel


class SocatTunnelManager(TunnelManager):
    """
    This is just a variation of `fabric.tunnels.TunnelManager` for allowing a flexible channel.
    """
    def __init__(self, local_host, local_port, remote_host, remote_port, transport, finished, socat_cmd, quiet):
        super().__init__(local_host, local_port, remote_host, remote_port, transport, finished)
        self._socat_cmd = socat_cmd
        self.quiet = quiet

    def get_channel(self, local_peer):
        channel = self.transport.open_channel('session')
        if channel is None:
            raise Exception("Failed to open channel on the SSH server.")
        if not self.quiet:
            print(self._socat_cmd)
        channel.exec_command(self._socat_cmd)
        return channel

    def _run(self):
        # Track each tunnel that gets opened during our lifetime
        tunnels = []

        # Set up OS-level listener socket on forwarded port
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # TODO: why do we want REUSEADDR exactly? and is it portable?
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # NOTE: choosing to deal with nonblocking semantics and a fast loop,
        # versus an older approach which blocks & expects outer scope to cause
        # a socket exception by close()ing the socket.
        sock.setblocking(0)
        sock.bind(self.local_address)
        sock.listen(1)

        while not self.finished.is_set():
            # Main loop-wait: accept connections on the local listener
            # NOTE: EAGAIN means "you're nonblocking and nobody happened to
            # connect at this point in time"
            try:
                tun_sock, local_addr = sock.accept()
                # Set TCP_NODELAY to match OpenSSH's forwarding socket behavior
                tun_sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            except socket.error as e:
                if e.errno is errno.EAGAIN:
                    # TODO: make configurable
                    time.sleep(0.01)
                    continue
                raise

            # Set up direct-tcpip channel on server end
            # TODO: refactor w/ what's used for gateways
            channel = self.get_channel(local_addr)

            # Set up 'worker' thread for this specific connection to our
            # tunnel, plus its dedicated signal event (which will appear as a
            # public attr, no need to track both independently).
            finished = Event()
            tunnel = Tunnel(channel=channel, sock=tun_sock, finished=finished)
            tunnel.start()
            tunnels.append(tunnel)

        exceptions = []
        # Propogate shutdown signal to all tunnels & wait for closure
        # TODO: would be nice to have some output or at least logging here,
        # especially for "sets up a handful of tunnels" use cases like
        # forwarding nontrivial HTTP traffic.
        for tunnel in tunnels:
            tunnel.finished.set()
            tunnel.join()
            wrapper = tunnel.exception()
            if wrapper:
                exceptions.append(wrapper)
        # Handle exceptions
        if exceptions:
            raise ThreadException(exceptions)

        # All we have left to close is our own sock.
        # TODO: use try/finally?
        sock.close()


class SocketTunnel(LocalTunnel):
    """
    Establish a tunnel from the local machine to the SSH host and from there start a **socat** process for forwarding
    traffic between the remote-end `stdout` and a Unix socket.

    :param remote_socket: Unix socket to connect to on the remote machine.
    :type remote_socket: unicode | str
    :param local_port: Local TCP port to use for the tunnel.
    :type local_port: int
    :param quiet: If set to ``False``, the **socat** command line on the SSH channel will be written to `stdout`.
    :type quiet: bool
    """
    def __init__(self, connection, remote_socket, local_port, quiet=None):
        super(SocketTunnel, self).__init__(connection, local_port)
        self.remote_socket = remote_socket
        if quiet is None:
            self.quiet = True
        else:
            self.quiet = quiet

    def get_tunnel_manager(self, *args, **kwargs):
        return SocatTunnelManager(
            local_port=self.bind_port,
            local_host=self.bind_host,
            remote_port=self.remote_port,
            remote_host=self.remote_host,
            transport=self.transport,
            finished=Event(),
            socat_cmd=' '.join(('socat', 'STDIO', 'UNIX-CONNECT:{0}'.format(self.remote_socket))),
            quiet=self.quiet
        )
