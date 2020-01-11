# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from threading import Event

from fabric.tunnels import TunnelManager
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


class LocalTunnel(object):
    """
    Forward a local port to a given host and port on the remote side.

    This is just a variation of `fabric.connection.Connection.forward_local` implemented without the
    context manager and adding an option to change the `TunnelManager`.

    :param remote_port: Remote port to forward connections to.
    :type remote_port: int
    :param remote_host: Host to connect to. Optional, default is ``localhost``.
    :type remote_host: unicode | str
    :param bind_port: Local port to bind to. Optional, default is same as ``remote_port``.
    :type bind_port: int
    :param bind_host: Local address to bind to. Optional, default is ``localhost``.
    """
    def __init__(self, connection, remote_port, remote_host=None, bind_port=None, bind_host=None):
        self.transport = connection.transport
        self.remote_port = remote_port
        self.remote_host = remote_host or 'localhost'
        self.bind_port = bind_port or remote_port
        self.bind_host = bind_host or 'localhost'
        self.connected = False
        self._finished = None
        self._manager = None

    def get_tunnel_manager(self):
        return TunnelManager(
            local_port=self.bind_port,
            local_host=self.bind_host,
            remote_port=self.remote_port,
            remote_host=self.remote_host,
            transport=self.transport,
            finished=Event()
        )

    def connect(self):
        self._manager = manager = self.get_tunnel_manager()
        self._finished = manager.finished
        manager.start()
        self.connected = True

    def close(self):
        self.connected = False
        finished = self._finished
        manager = self._manager
        # Signal to manager that it should close all open tunnels
        finished.set()
        # Then wait for it to do so
        manager.join()
        # Raise threading errors from within the manager, which would be
        # one of:
        # - an inner ThreadException, which was created by the manager on
        # behalf of its Tunnels; this gets directly raised.
        # - some other exception, which would thus have occurred in the
        # manager itself; we wrap this in a new ThreadException.
        # NOTE: in these cases, some of the metadata tracking in
        # ExceptionHandlingThread/ExceptionWrapper/ThreadException (which
        # is useful when dealing with multiple nearly-identical sibling IO
        # threads) is superfluous, but it doesn't feel worth breaking
        # things up further; we just ignore it for now.
        wrapper = manager.exception()
        if wrapper is not None:
            if wrapper.type is ThreadException:
                raise wrapper.value
            else:
                raise ThreadException([wrapper])
        self._finished = None
        self._manager = None
