# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import socket
import errno
import time
from threading import Event

from fabric.tunnels import TunnelManager, Tunnel
from invoke import ThreadException

"""
-- BSD 2-Clause due to code originally copied from Fabric, and modified below. --

Copyright (c) 2018 Jeff Forcier.
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

    * Redistributions of source code must retain the above copyright notice,
      this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright notice,
      this list of conditions and the following disclaimer in the documentation
      and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""


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
