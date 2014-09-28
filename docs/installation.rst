.. _installation_and_configuration:

==============================
Installation and configuration
==============================

Installation
============
The current stable release, published on PyPI_, can be installed using the following command:

.. code-block:: bash

   pip install docker-fabric


For importing YAML configurations for Docker-Map_, you can install Docker-Fabric using

.. code-block:: bash

   pip install docker-fabric[yaml]


Dependencies
------------
The following libraries will be automatically installed from PyPI.
* Fabric (tested with >=1.8.0)
* docker-py (>=0.5.0)
* docker-map (>=0.1.1)
* Optional: PyYAML (tested with 3.11) for YAML configuration import


Docker service
--------------
Docker needs to be installed on the target machine. On Ubuntu, you can use the task `install_docker` for automatically
installing and configuring the latest release. The following configuration is only needed if the service has been
installed otherwise.


Socat
-----
The tool Socat_ is needed in order to tunnel local TCP-IP connections to a unix socket on the target machine. You can
either install it yourself, or use the existing Fabric task `build_socat` (currently only Ubuntu) to build it directly
on your target machine.


Configuration
=============
Docker service
--------------
On every target machine, Docker-Fabric needs access to the Docker Remote API and (optionally) to the command line
client. In the default docker configuration, this means that the connecting SSH user needs to be in the `docker`
user group, in order to have access to the unix socket.

For assigning an existing user to that group, run

.. code-block:: bash

   usermod -aG docker <user name>


Note that if you run this command with the same user (using `sudo`), you need to re-connect. Use
`fabric.network.disconnect_all`_ if necessary.


Environment
-----------
In order to customize the general behavior of the client, the following variables can be set in Fabric's
:data:`~fabric.state.env`:

* ``docker_tunnel_remote_port``: Optional; to be set if the existing SSH connection will be used for tunnelling a local
  connection to the Docker Remote API. If a TCP connection is tunneled, this port should be the endpoint of the remote
  API (e.g. 443 if Docker is exposing a local HTTPS service); for unix connections, this will be used by `socat` to
  forward traffic between the SSH tunnel and the Docker socket.
* ``docker_base_url``: Optional, but to be set if the local connection is not on the local machine. If
  `docker_tunnel_remote_port`` is set, will be tunnelled through SSH, otherwise be simply passed to ``docker-py``. When
  tunneling an URL starting with ``http+unix:``, ``unix:``, or ``/`` (indicating a file path), `socat` will be used to
  bridge the TCP-IP connection to the socket. For example, set it to ``/var/run/docker.sock`` if Docker is running on the
  same machine that you are connecting to.
* ``docker_tunnel_local_port``: Optional; set this, if you are using a tunneled socket connection and for some reason
  want the local tunnel to have a different open port than the one on the remote end.
  Since a local port has to be available for each connection, the port is increased by one for each connection in order
  to handle multiple server connections. This means for example, that when setting this to 2224 and connecting to 10
  servers, ports from 2224 through 2234 will be temporarily occupied.
* ``docker_timeout``: Optional; by default uses :const:`~docker-py.docker.client.DEFAULT_TIMEOUT_SECONDS`.
* ``docker_api_version``: Optional; by default uses :const:`~docker-py.docker.client.DEFAULT_DOCKER_API_VERSION`.


Additionally, the following variables are specific for Docker registry access. They can be overridden in the relevant
commands (:func:`~dockerfabric.apiclient.DockerFabricClient.login`,
:func:`~dockerfabric.apiclient.DockerFabricClient.push`, and
:func:`~dockerfabric.apiclient.DockerFabricClient.pull`).

* ``docker_registry_user``: User name to use when authenticating against a Docker registry.
* `docker_registry_password``: Password to use when authenticating against a Docker registry.
* ``docker_registry_mail``: E-Mail to use when authenticating against a Docker registry.
* ``docker_registry_repository``: Optional; the registry to connect to. This will be expanded to a URL automatically.
  If not set, registry operations will run on the public Docker index.
* ``docker_registry_insecure``: Whether to set the `insecure` flag on Docker registry operations, e.g. when accessing your
  self-hosted registry over plain HTTP. Default is ``False``.


Checking the setup
==================
For checking if everything is set up properly, you can run the included task `check_version`. For example, running

.. code-block:: bash

   fab docker.check_version


against a local Vagrant machine (using the default setup, only allowing socket connections) and tunnelling through
port 2224 should show a similar result::

   [127.0.0.1] Executing task 'docker.check_version'
   socat TCP-LISTEN:2224,fork,reuseaddr UNIX-CONNECT:/var/run/docker.sock
   {u'KernelVersion': u'3.13.0-34-generic', u'Arch': u'amd64', u'ApiVersion': u'1.14', u'Version': u'1.2.0', u'GitCommit': u'fa7b24f', u'Os': u'linux', u'GoVersion': u'go1.3.1'}

   Done.
   Disconnecting from 127.0.0.1:2222... done.


.. _PyPI: https://pypi.python.org/pypi/docker-fabric
.. _Docker-Map: https://pypi.python.org/pypi/docker-map
.. _Socat: http://www.dest-unreach.org/socat/
.. _fabric.network.disconnect_all: http://fabric.readthedocs.org/en/latest/api/core/network.html#fabric.network.disconnect_all