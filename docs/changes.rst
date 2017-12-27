.. _change_history:

Change History
==============
0.5.0
-----
* Minor addition to CLI client.

0.5.0b4
-------
* Fixed image id parsing after successful build.

0.5.0b3
-------
* Added new CLI functions and utility task for volumes, as now implemented in Docker-Map 0.8.0b3.

0.5.0b2
-------
* Fixed setup (requirements).

0.5.0b1
-------
* Adapted to recent Docker-Map developments, which includes networking support and improved error handling.
* Dropped setup tasks for Docker and Socat. Socat is included in most Linux distributions, so that the task of compiling
  it from source was likely not used. Installation instructions for Docker have changed too frequently, and a correct
  (supported) setup depends strongly on the environment it is installed in, with more aspects than these simple tasks
  could consider.

0.4.2
-----
* Added ``top`` method to CLI client.

0.4.1
-----
* Fixed side-effects of modifying the ``base_url`` for SSH tunnels, causing problems when re-using a client returned
  by the ``docker_fabric()`` function (`Issue #12 <https://github.com/merll/docker-fabric/issues/12>`_).
* Added ``version`` method to CLI client.
* Added ``env.docker_cli_debug`` for echoing commands.
* API clients' ``remove_all_containers`` now forwards keyword arguments.

0.4.0
-----
* Added Docker-Map's new features (keeping certain tags during cleanup and adding extra tags during build).
* Added experimental :ref:`cli_client`. This has changed the module structure a bit, but previous imports should still work.
  From now on however, ``docker_fabric`` and ``container_fabric`` should be imported from ``dockerfabric.api`` instead
  of ``dockerfabric.apiclient``.
* Fixed installation task for CentOS.

0.3.10
------
* Updated Docker service installation to follow reference instructions.
* Added separate utility tasks for CentOS.
* Fixed build failures in case of unicode errors.

0.3.9
-----
* Client configuration is not required, if defaults are used.

0.3.8
-----
* Implemented local (faster) method for adjusting permissions on containers.
* Fixed issues with non-existing directories when downloading resources from containers.

0.3.7
-----
* Minor logging changes.
* Make it possible to set raise_on_error with pull (`PR #3 <https://github.com/merll/docker-fabric/pull/3>`_)

0.3.6
-----
* Added script and single-command actions.

0.3.5
-----
* docker-py update compatibility.

0.3.4
-----
* Added Fabric error handling when build fails.
* Fixed re-use of existing local tunnels when connections are opened through different methods.

0.3.3
-----
* More consistent arguments to connection behavior.

0.3.2
-----
* Added ``!env_lazy`` YAML tag.
* Fixed bug on local connections.

0.3.1
-----
* Added restart utility task.

0.3.0
-----
* Added Docker-Map's new features (host-client-configuration and multiple maps).

0.2.0
-----
* Revised SSH tunnelling of Docker service connections; not exposing a port on the host any longer.

0.1.4
-----
* Intermediate step to 0.2.0, not published on PyPI.
* Better tolerance on missing parameters.
* Improved multiprocessing behavior (parallel tasks in Fabric).

0.1.3
-----
* Only setup fix, no functional changes.

0.1.2
-----
* Added more utility tasks, functions, and context managers.
* Improved output format of builtin tasks.
* Cleanups and fixes in utility functions.

0.1.1
-----
* Added YAML import.
* Added default host root path and repository prefix.
* Added Docker registry actions.
* Added import/export utility functions.
* Attempts to fix reconnect and multiple connection issues.

0.1.0
-----
Initial release.
