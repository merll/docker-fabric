Docker-Fabric
=============

Integration of Docker deployments into Fabric.
----------------------------------------------

Project: https://github.com/merll/docker-fabric

Docs: https://docker-fabric.readthedocs.org/en/latest/


Overview
========
With a few preparations, Docker images can easily be generated and tested on development
machines, and transferred on to a production environment.  This package is based on
[Docker-Map](https://github.com/merll/docker-map), and therefore supports managing
container configurations along with their dependencies within Fabric-based deployments.
Wherever possible, the library makes calls to the Remote API; for certain features (e.g.
extracting container contents) the Docker command-line interface (CLI) is used.

API access
==========
As with Docker-Map, container configurations can be generated as objects, updated from
Python dictionaries, or imported from YAML files in order to control remote clients
via the API. Docker-Fabric includes the following enhancements:

Docker client
-------------
`DockerFabricClient` is an implementation of Docker-Map's `DockerClientWrapper`. It
adds Fabric-like logging in the context of container instances on top of Fabric hosts,
and enables automatic creation of tunnel connections for access to a remote Docker host
using Fabric's SSH connection.

By using the tool `socat`, a Docker client can be used on a remote machine through an
existing SSH tunnel, without re-configuring Docker to enable access by a TCP port. If you
have already done that, you can still use a local SSH tunnel for avoiding exposing
Docker outside of `localhost`, as that is not recommended.

Client configuration
--------------------
`DockerClientConfiguration` is extending `ClientConfiguration`, and adds the capability
of running containers to Fabric hosts with specific Docker settings for each.

Running container configurations
--------------------------------
`ContainerFabric` is a simple wrapper that combines Docker-Map's `DockerFabricClient`,
`DockerClientConfiguration` objects, and container mmaps.

Command-line based access
-------------------------
Provides the following features by running the appropriate commands on a remote Docker
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
(e.g. `update`) can be triggered from the command line as Fabric tasks.

Additionally the following tasks are included in this package, that can be run by Fabric
directly:

* `install_docker`: Install Docker on a remote machine (to be adapted to more
  distributions). Uses the latest released version for Ubuntu.
* `build_socat`: Download and install the tool `socat`. This is used to build a tunneled
  access to a remote Docker, if it is only accessible through a local socket.
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
