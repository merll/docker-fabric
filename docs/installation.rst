.. _installation_and_configuration:

Installation and configuration
==============================

Installation
------------
The current stable release, published on PyPI_, can be installed using the following command:

.. code-block:: bash

   pip install docker-fabric


For importing YAML configurations for Docker-Map_, you can install Docker-Fabric using

.. code-block:: bash

   pip install docker-fabric[yaml]


Dependencies
^^^^^^^^^^^^
The following libraries will be automatically installed from PyPI:

* Fabric (tested with >=1.8.0)
* docker-py (>=1.9.0)
* docker-map (>=0.8.0)
* Optional: PyYAML (tested with 3.11) for YAML configuration import


Docker service
^^^^^^^^^^^^^^
Docker needs to be installed on the target machine. There used to be a utility task for this, but the required steps for
installation tended to change too much too quickly for maintaining them properly. Please follow the
`Docker installation instructions`_ according to your operating system.


Socat
^^^^^
The tool Socat_ is needed in order to tunnel local TCP-IP connections to a unix socket on the target machine. The
``socat`` binary needs to be in the search path. It is included in most common Linux distributions, e.g. for CentOS
you can install it using ``yum install socat``; or you can download the source code and compile it yourself.


Configuration
-------------

Docker service
^^^^^^^^^^^^^^
On every target machine, Docker-Fabric needs access to the Docker Remote API and (optionally) to the command line
client. With the default Docker configuration, this requires for the connecting SSH user to be in the `docker`
user group. The group assignment provides access to the unix socket.

For assigning an existing user to that group, run

.. code-block:: bash

   usermod -aG docker <user name>


Note that if you run this command with the same user (using `sudo`), you need to re-connect. Use
:func:`~fabric.network.disconnect_all` if necessary.


Tasks
^^^^^
If you plan to use the built-in tasks, include the module in your fabfile module (e.g. `fabfile.py`). Most likely
you might want to assign an alias for the task namespace::

    from dockerfabric import tasks as docker


.. _fabric_env:

Environment
^^^^^^^^^^^
In order to customize the general behavior of the client, the following variables can be set in `Fabric's env`_. All
of them are generally optional, but some are needed when tunnelling connections over SSH:

* ``docker_base_url``: The URL of the Docker service. If not set, defaults to a socket connection in
  ``/var/run/docker.sock``, which is also the default behavior of the `docker-py` client.
  If ``docker_tunnel_remote_port`` and/or ``docker_tunnel_local_port`` is set, the connection will be tunnelled through
  SSH, otherwise the value is simply passed to `docker-py`. For socket connections (i.e. this is blank, starts with
  a forward slash, or is prefixed with ``http+unix:``, ``unix:``), **socat** will be used to forward the TCP-IP tunnel
  to the socket.
* ``docker_tunnel_local_port``: Set this, if you need a tunneled socket connection. Alternatively, the value
  ``docker_tunnel_remote_port`` is used (unless empty as well). This is the first local port for tunnelling
  connections to a Docker service on the remote. Since during simultaneous connections, a separate local port has to be
  available for each, the port number is increased by one on every new connection. This means for example, that when
  setting this to 2224 and connecting to 10 servers, ports from 2224 through 2233 will be temporarily occupied.
* ``docker_tunnel_remote_port``: Port of the Docker service.

  - On TCP connections, this is the remote endpoint of the tunnel. If a different port is included in
    ``docker_base_url``, this setting is ignored.
  - For socket connections, this is the initial local tunnel port. If specified by ``docker_tunnel_local_port``, this
    setting has no effect.

* ``docker_timeout``: Request timeout of the Docker service; by default uses
  :const:`~docker-py.docker.client.DEFAULT_TIMEOUT_SECONDS`.
* ``docker_api_version``: API version used to communicate with the Docker service, as a string, such as ``1.16``.
  Must be lower or equal to the accepted version. By default uses
  :const:`~docker-py.docker.client.DEFAULT_DOCKER_API_VERSION`.


Additionally, the following variables are specific for Docker registry access. They can be overridden in the relevant
commands (:meth:`~dockerfabric.apiclient.DockerFabricClient.login`,
:meth:`~dockerfabric.apiclient.DockerFabricClient.push`, and
:meth:`~dockerfabric.apiclient.DockerFabricClient.pull`).

* ``docker_registry_user``: User name to use when authenticating against a Docker registry.
* ``docker_registry_password``: Password to use when authenticating against a Docker registry.
* ``docker_registry_mail``: E-Mail to use when authenticating against a Docker registry.
* ``docker_registry_repository``: Optional; the registry to connect to. This will be expanded to a URL automatically.
  If not set, registry operations will run on the public Docker index.
* ``docker_registry_insecure``: Whether to set the `insecure` flag on Docker registry operations, e.g. when accessing your
  self-hosted registry over plain HTTP. Default is ``False``.


Examples
^^^^^^^^
For connecting to a remote Docker instance over a socket, install **socat** on the remote, and put the following in
your ``fabfile``::

    from fabric.api import env
    from dockerfabric import tasks as docker

    env.docker_tunnel_local_port = 22024  # or any other available port above 1024 of your choice


If the remote Docker instance accepts connections on port 8000 from localhost (not recommended), use the following::

    from fabric.api import env
    from dockerfabric import tasks as docker

    env.docker_base_url = 'tcp://127.0.0.1:8000'
    env.docker_tunnel_local_port = 22024  # or any other available port above 1024 of your choice


Checking the setup
------------------
For checking if everything is set up properly, you can run the included task `version`. For example, running

.. code-block:: bash

   fab docker.version


against a local Vagrant machine (using the default setup, only allowing socket connections) and tunnelling through
port 2224 should show a similar result::

    [127.0.0.1] Executing task 'docker.version'
    [127.0.0.1]
    KernelVersion: 3.13.0-34-generic
    Arch:          amd64
    ApiVersion:    1.14
    Version:       1.2.0
    GitCommit:     fa7b24f
    Os:            linux
    GoVersion:     go1.3.1

    Done.
    Disconnecting from 127.0.0.1:2222... done.


.. _PyPI: https://pypi.python.org/pypi/docker-fabric
.. _Docker-Map: https://pypi.python.org/pypi/docker-map
.. _Socat: http://www.dest-unreach.org/socat/
.. _Fabric's env: http://docs.fabfile.org/en/latest/usage/env.html
.. _Docker installation instructions: https://docs.docker.com/engine/installation/
