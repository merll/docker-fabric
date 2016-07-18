# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from fabric.api import env

from .apiclient import DockerFabricApiConnections, ContainerApiFabricClient
from .cli import DockerCliConnections, ContainerCliFabricClient

CLIENT_API = 'API'
CLIENT_CLI = 'CLI'

docker_api = DockerFabricApiConnections().get_connection
docker_cli = DockerCliConnections().get_connection


def docker_fabric(*args, **kwargs):
    """
    :param args: Positional arguments to Docker client.
    :param kwargs: Keyword arguments to Docker client.
    :return: Docker client.
    :rtype: dockerfabric.apiclient.DockerFabricClient | dockerfabric.cli.DockerCliClient
    """
    ci = kwargs.get('client_implementation') or env.get('docker_fabric_implementation') or CLIENT_API
    if ci == CLIENT_API:
        return docker_api(*args, **kwargs)
    elif ci == CLIENT_CLI:
        return docker_cli(*args, **kwargs)
    raise ValueError("Invalid client implementation.", ci)


def container_fabric(container_maps=None, docker_client=None, clients=None, client_implementation=None):
    """
    :param container_maps: Container map or a tuple / list thereof.
    :type container_maps: list[dockermap.map.container.ContainerMap] | dockermap.map.container.ContainerMap
    :param docker_client: Default Docker client instance.
    :type docker_client: DockerClientConfiguration or docker.docker.Client
    :param clients: Optional dictionary of Docker client configuration objects.
    :type clients: dict[unicode | str, DockerClientConfiguration]
    :param client_implementation: Client implementation to use (API or CLI).
    :type client_implementation: unicode | str
    :return: Container mapping client.
    :rtype: dockerfabric.base.FabricContainerClient
    """
    ci = client_implementation or env.get('docker_fabric_implementation') or CLIENT_API
    if ci == CLIENT_API:
        return ContainerApiFabricClient(container_maps, docker_client, clients)
    elif ci == CLIENT_CLI:
        return ContainerCliFabricClient(container_maps, docker_client, clients)
    raise ValueError("Invalid client implementation.", ci)
