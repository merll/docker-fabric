# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import collections
import ctypes
import logging
import multiprocessing

import six

from dockermap.api import MappingDockerClient, ContainerMap
from dockermap.docker_api import INSECURE_REGISTRIES

log = logging.getLogger(__name__)
port_offset = multiprocessing.Value(ctypes.c_ulong)


def _get_config_clients(host, client_configs, cls):
    if not client_configs:
        return {}, cls()
    clients = {}
    default_client = None
    for client_name, client_cfg in six.iteritems(client_configs):
        if isinstance(client_cfg, dict):
            cfg_obj = cls()
            cfg_obj.update(client_cfg)
        else:
            cfg_obj = client_cfg
        clients[client_name] = cfg_obj
        if cfg_obj.get('fabric_host') == host:
            default_client = cfg_obj
    return clients, default_client


def _get_map_clients(container_map, all_client_names):
    map_clients = set(container_map.clients or ())
    for config_name, c_config in container_map:
        if c_config.clients:
            map_clients.update(c_config.clients)
    missing_client_names = map_clients - all_client_names
    if missing_client_names:
        raise ValueError("Clients '{0}' used in map '{1}' not configured."
                         .format(','.join(missing_client_names), container_map.name))
    return map_clients


def get_client_kwargs(connection, map_configs, client_configs, client_cls):
    cfg = connection.config.get('docker', {})
    client_configs = client_configs or cfg.get('clients', {})
    map_configs = map_configs or cfg.get('maps', ())
    all_clients, default_client = _get_config_clients(connection.host, client_configs, client_cls)
    default_client.connection = connection
    if isinstance(map_configs, dict):
        mi = six.iteritems(map_configs)
    elif isinstance(map_configs, ContainerMap):
        mi = (map_configs.name, map_configs),
    elif isinstance(map_configs, collections.Iterable):
        mi = map_configs
    else:
        raise ValueError("Configured type of maps must be iterable, found type {0}.".format(type(map_configs).__name__))

    maps = {}
    all_client_names = set(all_clients.keys())
    used_client_names = set()
    for map_name, map_cfg in mi:
        print(map_name)
        if isinstance(map_cfg, dict):
            cfg_obj = ContainerMap(map_name, map_cfg)
        elif isinstance(map_cfg, ContainerMap):
            cfg_obj = map_cfg
        else:
            raise ValueError("Container maps must be either dictionaries or ContainerMap objects. Found type {0}"
                             .format(type(map_cfg).__name__))
        map_client_names = _get_map_clients(cfg_obj, all_client_names)
        used_client_names.update(map_client_names)
        maps[map_name] = cfg_obj

    current_clients = {}
    for client_name in used_client_names:
        client_config = all_clients.get(client_name)
        client_host = client_config.get('fabric_host')
        if not client_host:
            raise ValueError("Client '{0}' is configured, but has no 'fabric_host' definition.".format(client_name))
        current_clients[client_name] = client_config

    return maps, default_client, current_clients


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
            c_maps, default_client, current_clients = get_client_kwargs(connection, container_maps, clients,
                                                                        self.configuration_class)
            super(FabricContainerClient, self).__init__(container_maps=c_maps, docker_client=default_client,
                                                        clients=current_clients)
        else:
            super(FabricContainerClient, self).__init__(container_maps=container_maps, docker_client=docker_client,
                                                        clients=clients)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


def get_local_port(init_port):
    with port_offset.get_lock():
        current_offset = port_offset.value
        port_offset.value += 1
    return int(init_port) + current_offset
