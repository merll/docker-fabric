# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from fabric.network import needs_host
from fabric.state import env, connections

from .tunnel import LocalTunnel


class SocketTunnels(dict):
    """
    Cache for `socat` tunnels to the remote machine.
    """
    def __getitem__(self, item):
        """
        :param item: Tuple of remote socket name, remote port, and local port number.
        :type item: tuple
        :return: Socket tunnel
        :rtype: SocketTunnel
        """
        remote_socket, remote_port, local_port = item
        key = env.host_string, remote_socket
        svc = self.get(key)
        if not svc:
            svc = SocketTunnel(remote_socket, remote_port, local_port)
            svc.connect()
            self[key] = svc
        return svc


socat_tunnels = SocketTunnels()


class SocatService(object):
    """
    Utility class for running `socat`.

    :param dest: Destination parameter for `socat`.
    :type dest: unicode
    :param src: Source parameter for `socat`.
    :type src: unicode
    :param quiet: Optional (default is `False`). If set to `True`, the command line on the SSH channel will not
      be written to `stdout`.
    :type quiet: bool
    """
    def __init__(self, dest, src, quiet=False):
        self.dest = dest
        self.src = src
        self.quiet = quiet
        self.channel = None

    @needs_host
    def connect(self):
        """
        Opens a channel through a SSH connection to ``env.host_string`` (which will be opened by Fabric if necessary)
        and launches `socat`.
        """
        transport = connections[env.host_string].get_transport()
        self.channel = transport.open_channel('session')
        cmd = ' '.join(('socat', self.dest, self.src))
        if not self.quiet:
            print(cmd)
        self.channel.exec_command(cmd)

    def close(self):
        """
        Closes the channel for `socat`.
        """
        self.channel.close()


class SocketTunnel(LocalTunnel):
    """
    Establish a tunnel from the local machine to the SSH host and from there start a `socat` process for forwarding
    traffic between the remote-end TCP port and a Unix socket.

    :param remote_socket: Unix socket to connect to on the remote machine.
    :type remote_socket: unicode
    :param remote_port: Remote-end TCP port to use for the tunnel.
    :type remote_port: int
    :param local_port: Local TCP port to use for the tunnel.
    :type local_port: int
    :param quiet: If set to `True`, the command line on the SSH channel will not be written to `stdout`.
    :type quiet: bool
    """
    def __init__(self, remote_socket, remote_port, local_port, quiet=False):
        dest = 'TCP-LISTEN:{0},fork,reuseaddr'.format(remote_port)
        src = 'UNIX-CONNECT:{0}'.format(remote_socket)
        self.socat_service = SocatService(dest, src, quiet)
        super(SocketTunnel, self).__init__(remote_port, bind_port=local_port)

    def connect(self):
        """
        Establishes the local tunnel and the `socat` channel.
        """
        self.socat_service.connect()
        super(SocketTunnel, self).connect()

    def close(self):
        """
        Closes the `socat` channel and the local tunnel.
        """
        try:
            super(SocketTunnel, self).close()
        finally:
            self.socat_service.close()
