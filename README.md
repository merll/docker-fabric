Docker-Fabric
=============

Build Docker images, and run Docker containers in Fabric.
---------------------------------------------------------

Project: https://github.com/merll/docker-fabric

Docs: https://docker-fabric.readthedocs.io/en/latest/


Overview
========
With a few preparations, Docker images can easily be generated and tested on development
machines, and transferred on to a production environment. This package supports managing
container configurations along with their dependencies within Fabric-based deployments.
DockerFiles can also be easily implemented in Fabric tasks.

Local Docker clients can be controlled directly through ``docker-py``. Remote Docker
API services make use of Fabric's SSH connection.

API access
==========
This project is based on [Docker-Map](https://github.com/merll/docker-map), and adapts
its container configuration methods.

As with Docker-Map, container configurations can be generated as objects, updated from
Python dictionaries, or imported from YAML files in order to control remote clients
via the API. Docker-Fabric includes the following enhancements:

Docker client
-------------
`DockerFabricClient` adds Fabric-like logging in the context of container instances on
top of Fabric hosts, and enables automatic creation of tunnel connections for access to a
remote Docker host using Fabric's SSH connection. By using the tool `socat`, the Docker
client can access a remote service without re-configuration.

Client configuration
--------------------
`DockerClientConfiguration` adds the capability of running containers to Fabric hosts
with specific Docker settings for each, e.g. the version number.

Running container configurations
--------------------------------
`ContainerFabric` is a simple wrapper that combines Docker-Map's `DockerFabricClient`,
`DockerClientConfiguration` objects, and container maps.

Command-line based access
-------------------------
The following features are provided by running the appropriate commands on a remote Docker
command line:

* Copy resources from a container to a Fabric host.
* Copy resources from a container and download them in a compressed tarball. The Docker
  Remote API currently does not support creating compressed tarballs.
* Copy resources from a container and store them in a new blank image.
* Generate a compressed image tarball. The Docker Remote API currently does not support
  creating compressed tarballs, but is capable of importing them.

Tasks
=====
All essential container actions (`create`, `start`, `stop`, `remove`) and some advanced
(e.g. `update`) can be triggered from the command line as Fabric tasks and executed on
the remote service, e.g. via SSH.

Additionally the following tasks are included in this package, that can be run by Fabric
directly:

* `check_version`: Returns version information of the remote Docker service and provides
  useful insight if permissions are set up properly.
* `cleanup_containers`: Removes all containers that have stopped.
* `cleanup_images`: Removes all untagged images, that do not have a dependent container
  or other dependent images.
* `remove_all_containers`: Stops and removes all containers on the remote Docker service.


Contributions
=============
Thanks to [lfasnacht](https://github.com/lfasnacht) for publishing an implementation for
a local tunnel to a Fabric client in the [pull request 939 of Fabric](https://github.com/fabric/fabric/pull/939).

Further contributions are maintained in [CONTRIBUTIONS.md](https://github.com/merll/docker-fabric/blob/master/CONTRIBUTIONS.md) of the project.
