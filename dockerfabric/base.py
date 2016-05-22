# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import ctypes
import multiprocessing

from dockermap.map.config import ClientConfiguration
from fabric.api import env, settings

port_offset = multiprocessing.Value(ctypes.c_ulong)


class ConnectionDict(dict):
    def get(self, k, d, *args, **kwargs):
        e = super(ConnectionDict, self).get(k)
        if e is None:
            e = d(*args, **kwargs)
            self[k] = e
        return e


class DockerConnectionDict(ConnectionDict):
    """
    Cache for connections to Docker clients.
    """
    client_class = None

    def get_connection(self, *args, **kwargs):
        """
        Create a new connection, or return an existing one from the cache. Uses Fabric's current ``env.host_string``
        and the URL to the Docker service.

        :param args: Additional arguments for the client constructor, if a new client has to be instantiated.
        :param kwargs: Additional keyword args for the client constructor, if a new client has to be instantiated.
        :rtype: DockerFabricClient
        """
        key = env.get('host_string'), kwargs.get('base_url', env.get('docker_base_url'))
        return self.get(key, self.client_class, *args, **kwargs)


class FabricClientConfiguration(ClientConfiguration):
    def get_client(self):
        if 'fabric_host' in self:
            with settings(host_string=self.fabric_host):
                return super(FabricClientConfiguration, self).get_client()
        return super(FabricClientConfiguration, self).get_client()


def get_local_port(init_port):
    with port_offset.get_lock():
        current_offset = port_offset.value
        port_offset.value += 1
    return int(init_port) + current_offset
