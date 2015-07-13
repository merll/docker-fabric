.. _change_history:

Change History
==============

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
