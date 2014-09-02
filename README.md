docker-fabric
=============

Integration for Docker into Fabric.
-----------------------------------

Project: https://github.com/merll/docker-fabric


Overview
========
With a few preparations, Docker images can easily be generated and tested on development
machines, and transferred on to a production environment.  This package is based on
[docker-map](https://github.com/merll/docker-map), and helps to use Docker on
Fabric-based deployments. Wherever possible, the Remote API is used; for certain features
(e.g. extracting container contents) the Docker command-line interface (CLI) is used.

API access
==========

`DockerFabricClient`
--------------------
An implementation of `docker-map`'s `DockerClientWrapper`. Adds Fabric-like logging in
the context of container instances on top of Fabric hosts, and enables automatic
creation of tunnel connections for access to a remote Docker host using Fabric's SSH
connection.

By using the tool `socat`, a Docker client can be used on a remote machine through an
existing SSH tunnel, without re-configuring Docker to enable access by a TCP port. If you
have already done that, you can still use a local SSH tunnel for avoiding exposing
Docker outside of `localhost`, as that is not recommended.

`ContainerFabric`
-----------------
Simple wrapper for `docker-map`'s `MappingClient` to `DockerFabricClient`.

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
The following tasks are included in this package, that can be run by Fabric directly:

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

Once it has been merged into Fabric, it may be removed from this package.


Todo
====
* More detailed documentation.
* Unit tests.
