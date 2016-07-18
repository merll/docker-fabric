# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import ctypes
import multiprocessing

from dockermap.api import MappingDockerClient, ClientConfiguration
from fabric.api import env, settings

port_offset = multiprocessing.Value(ctypes.c_ulong)


def _get_default_config(client_configs):
    clients = client_configs or env.get('docker_clients')
    host_string = env.get('host_string')
    if not host_string or not clients:
        return None
    for c in clients.values():
        host = c.get('fabric_host')
        if host == host_string:
            return c
    return None


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
        """
        key = env.get('host_string'), kwargs.get('base_url', env.get('docker_base_url'))
        return self.get(key, self.client_class, *args, **kwargs)


class FabricClientConfiguration(ClientConfiguration):
    def get_client(self):
        if 'fabric_host' in self:
            with settings(host_string=self.fabric_host):
                return super(FabricClientConfiguration, self).get_client()
        return super(FabricClientConfiguration, self).get_client()


class FabricContainerClient(MappingDockerClient):
    """
    Convenience class for using a :class:`~dockermap.map.container.ContainerMap` on a :class:`DockerFabricClient`.

    :param container_maps: Container map or a tuple / list thereof.
    :type container_maps: list[dockermap.map.container.ContainerMap] | dockermap.map.container.ContainerMap
    :param docker_client: Default Docker client instance.
    :type docker_client: FabricClientConfiguration
    :param clients: Optional dictionary of Docker client configuration objects.
    :type clients: dict[unicode | str, FabricClientConfiguration]
    """
    def __init__(self, container_maps=None, docker_client=None, clients=None):
        all_maps = container_maps or env.get('docker_maps', ())
        if not isinstance(all_maps, (list, tuple)):
            env_maps = all_maps,
        else:
            env_maps = all_maps
        all_configs = clients or env.get('docker_clients', dict())
        current_clients = dict()

        default_client = docker_client or _get_default_config(all_configs)
        for c_map in env_maps:
            map_clients = set(c_map.clients or ())
            for config_name, c_config in c_map:
                if c_config.clients:
                    map_clients.update(c_config.clients)
            for map_client in map_clients:
                if map_client not in current_clients:
                    client_config = all_configs.get(map_client)
                    if not client_config:
                        raise ValueError("Client '{0}' used in map '{1}' not configured.".format(map_client, c_map.name))
                    client_host = client_config.get('fabric_host')
                    if not client_host:
                        raise ValueError("Client '{0}' is configured, but has no 'fabric_host' definition.".format(map_client))
                    current_clients[map_client] = client_config

        if not (default_client or clients):
            default_client = self.configuration_class()
        super(FabricContainerClient, self).__init__(container_maps=all_maps, docker_client=default_client,
                                                    clients=current_clients)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


def get_local_port(init_port):
    with port_offset.get_lock():
        current_offset = port_offset.value
        port_offset.value += 1
    return int(init_port) + current_offset
