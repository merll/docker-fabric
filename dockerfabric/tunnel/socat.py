# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from threading import Event

from .local import LocalTunnel
from .socat_manager import SocatTunnelManager


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
