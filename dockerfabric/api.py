# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from fabric.api import env

from .apiclient import DockerFabricApiConnections
from .cli import DockerCliConnections

CLIENT_API = 'API'
CLIENT_CLI = 'CLI'

docker_api = DockerFabricApiConnections().get_connection
docker_cli = DockerCliConnections().get_connection


def docker_fabric(*args, **kwargs):
    ci = kwargs.get('client_implementation') or env.get('docker_fabric_implementation') or CLIENT_CLI
    if ci == CLIENT_API:
        return docker_api(*args, **kwargs)
    elif ci == CLIENT_CLI:
        return docker_cli(*args, **kwargs)
    raise ValueError("Invalid client implementation.", ci)
