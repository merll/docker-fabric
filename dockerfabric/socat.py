# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import six
from fabric.state import env, connections

from .tunnel import LocalTunnel


class SocketTunnels(dict):
    def __getitem__(self, item):
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
    def __init__(self, dest, src, quiet=False):
        self.dest = dest
        self.src = src
        self.quiet = quiet
        self.channel = None

    def connect(self):
        transport = connections[env.host_string].get_transport()
        self.channel = transport.open_channel('session')
        cmd = ' '.join(('socat', self.dest, self.src))
        if not self.quiet:
            print(cmd)
        self.channel.exec_command(cmd)

    def close(self):
        self.channel.close()


class SocketTunnel(LocalTunnel):
    def __init__(self, remote_socket, remote_port, local_port, quiet=False):
        dest = ':'.join(('TCP-LISTEN', six.text_type(remote_port)))
        src = ':'.join(('UNIX-CONNECT', six.text_type(remote_socket)))
        self.socat_service = SocatService(dest, src, quiet)
        super(SocketTunnel, self).__init__(remote_port, bind_port=local_port)

    def connect(self):
        self.socat_service.connect()
        super(SocketTunnel, self).connect()

    def close(self):
        try:
            super(SocketTunnel, self).close()
        finally:
            self.socat_service.close()
