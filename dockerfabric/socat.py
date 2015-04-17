# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from fabric.state import env
from fabric.utils import puts

from .base import ConnectionDict, get_local_port
from .tunnel import LocalTunnel


class SocketTunnels(ConnectionDict):
    """
    Cache for **socat** tunnels to the remote machine.

    Instantiation of :class:`SocketTunnel` can be configured with ``env.socat_quiet``, setting
    the ``quiet`` keyword argument.
    """
    def __getitem__(self, item):
        """
        :param item: Tuple of remote socket name, remote port, and local port number.
        :type item: tuple
        :return: Socket tunnel
        :rtype: SocketTunnel
        """
        def _connect_socket_tunnel():
            local_port = get_local_port(init_local_port)
            svc = SocketTunnel(remote_socket, local_port, env.get('socat_quiet', True))
            svc.connect()
            return svc

        remote_socket, init_local_port = item
        key = env.host_string, remote_socket
        return self.get(key, _connect_socket_tunnel)


socat_tunnels = SocketTunnels()


class SocketTunnel(LocalTunnel):
    """
    Establish a tunnel from the local machine to the SSH host and from there start a **socat** process for forwarding
    traffic between the remote-end `stdout` and a Unix socket.

    :param remote_socket: Unix socket to connect to on the remote machine.
    :type remote_socket: unicode
    :param local_port: Local TCP port to use for the tunnel.
    :type local_port: int
    :param quiet: If set to ``False``, the **socat** command line on the SSH channel will be written to `stdout`.
    :type quiet: bool
    """
    def __init__(self, remote_socket, local_port, quiet=True):
        dest = 'STDIO'
        src = 'UNIX-CONNECT:{0}'.format(remote_socket)
        self.quiet = quiet
        self._socat_cmd = ' '.join(('socat', dest, src))
        super(SocketTunnel, self).__init__(local_port)

    def get_channel(self, transport, remote_addr, local_peer):
        channel = transport.open_channel('session')
        if channel is None:
            raise Exception("Failed to open channel on the SSH server.")
        if not self.quiet:
            puts(self._socat_cmd)
        channel.exec_command(self._socat_cmd)
        return channel
