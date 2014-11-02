.. _getting_started:

Getting started
===============

In order to connect with the Docker service, make sure that

1. Docker is installed on the remote machine;
2. **socat** is installed, if you are using the SSH tunnel;
3. and the SSH user has access to the service.

(For details, refer to :ref:`installation_and_configuration`).


Calls to the Remote API can be made by using :func:`~dockerfabric.apiclient.docker_fabric`. This function uses Fabric's
usual SSH connection (creates a new one if necessary) and opens a separate channel for forwarding requests to the
Docker Remote API.

Since this is merely a wrapper, all commands to ``docker-py`` are supported. Some additional functionality is provided
by Docker-Map. However, instead of repeatedly passing in similar parameters (e.g. the service URL), settings can be
preset globally for the project. Additionally, it provides a caching functionality for open tunnels and connections,
which speeds up access to Docker significantly.


Short examples::

   from dockerfabric.apiclient import docker_fabric
   docker_fabric().version()

returns version information from the installed Docker service. This function is directly passed through to
``docker-py`` and formatted. The utility function::

   docker_fabric().cleanup_containers()

removes all containers on the target Docker service that have exited.

For building images, use Docker-Map's :class:`~dockermap.build.dockerfile.DockerFile` for generating an environment,
and run::

   docker_fabric().build_from_file(dockerfile, 'new_image_tag:1.0', rm=True)

