# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import ctypes
import logging
import multiprocessing

from dockermap.api import MappingDockerClient

log = logging.getLogger(__name__)
port_offset = multiprocessing.Value(ctypes.c_ulong)


def _get_default_config(connection, client_configs):
    if not connection:
        return None
    host_string = connection.host
    conn_config = connection.config.get('docker', {})
    clients = client_configs or conn_config.get('clients')
    if not clients:
        return None
    for c in clients.values():
        host = c.get('fabric_host')
        if host == host_string:
            return c
    return None


class FabricContainerClient(MappingDockerClient):
    """
    Convenience class for using a :class:`~dockermap.map.config.main.ContainerMap` on a :class:`DockerFabricClient`.

    :param container_maps: Container map or a tuple / list thereof.
    :type container_maps: list[dockermap.map.config.main.ContainerMap] | dockermap.map.config.main.ContainerMap
    :param docker_client: Default Docker client instance.
    :type docker_client: FabricClientConfiguration
    :param clients: Optional dictionary of Docker client configuration objects.
    :type clients: dict[unicode | str, FabricClientConfiguration]
    """
    def __init__(self, connection, container_maps=None, docker_client=None, clients=None):
        self.connection = connection
        if connection:
            conn_config = connection.config.get('docker', {})
        else:
            conn_config = {}
        all_maps = container_maps or conn_config.get('maps', ())
        if not isinstance(all_maps, (list, tuple)):
            env_maps = all_maps,
        else:
            env_maps = all_maps
        all_configs = clients or conn_config.get('clients', dict())
        current_clients = dict()

        default_client = docker_client or _get_default_config(connection, all_configs)
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
