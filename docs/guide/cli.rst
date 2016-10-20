.. _cli_client:

Remote CLI client
=================
Following a `feature request on GitHub <https://github.com/merll/docker-fabric/issues/7>`_, an alternative client
implementation has been added to Docker-Fabric and Docker-Map, for using a command-line-based interface to Docker. It
supports the same options, methods, and arguments. However, it directly runs commands through Fabric instead of opening
its an additional SSH channel. Due to different requirements in parsing output and handling errors this should be
considered experimental.

Usage is very similar to the API client. There are two ways of changing between the two implementations:

#. By setting a Fabric environment variable::

    from fabric.api import env
    from dockerfabric.api import docker_fabric, container_fabric, CLIENT_CLI

    env.docker_fabric_implementation = CLIENT_CLI  # Default is CLIENT_API.


   This is the preferred method, as this also applies to utility tasks defined in Docker-Fabric.

#. Directly by importing a different method::

    from dockerfabric.cli import docker_cli, container_cli

    docker_cli().images()  # Instead of docker_fabric().images()
    container_cli().update(config_name)  # Instead of container_fabric().update(config_name)

