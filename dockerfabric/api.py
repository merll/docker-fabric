# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from .apiclient import DockerFabricClient, ContainerApiFabricClient
from .cli import DockerCliClient, ContainerCliFabricClient

CLIENT_API = 'API'
CLIENT_CLI = 'CLI'


def docker_fabric(c, **kwargs):
    """
    :param c: connection
    :type c: fabric.Connection
    :param kwargs: Keyword arguments to Docker client.
    :return: Docker client.
    :rtype: dockerfabric.apiclient.DockerFabricClient | dockerfabric.cli.DockerCliClient
    """
    config = c.config.get('docker', {})
    ci = kwargs.get('client_implementation') or config.get('client_implementation') or CLIENT_API
    if ci == CLIENT_API:
        return DockerFabricClient(connection=c, **kwargs)
    elif ci == CLIENT_CLI:
        return DockerCliClient(connection=c, **kwargs)
    raise ValueError("Invalid client implementation.", ci)


def container_fabric(c, container_maps=None, docker_client=None, clients=None, client_implementation=None):
    """
    :param c: connection
    :type c: fabric.Connection
    :param container_maps: Container map or a tuple / list thereof.
    :type container_maps: list[dockermap.map.config.main.ContainerMap] | dockermap.map.config.main.ContainerMap
    :param docker_client: Default Docker client instance.
    :type docker_client: dockerfabric.base.FabricClientConfiguration or docker.docker.Client
    :param clients: Optional dictionary of Docker client configuration objects.
    :type clients: dict[unicode | str, dockerfabric.base.FabricClientConfiguration]
    :param client_implementation: Client implementation to use (API or CLI).
    :type client_implementation: unicode | str
    :return: Container mapping client.
    :rtype: dockerfabric.base.FabricContainerClient
    """
    config = c.config.get('docker', {})
    ci = client_implementation or config.get('client_implementation') or CLIENT_API
    if ci == CLIENT_API:
        return ContainerApiFabricClient(c, container_maps, docker_client, clients)
    elif ci == CLIENT_CLI:
        return ContainerCliFabricClient(c, container_maps, docker_client, clients)
    raise ValueError("Invalid client implementation.", ci)
