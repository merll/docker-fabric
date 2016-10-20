.. _api_client:

Docker Remote API client for Fabric
===================================
:class:`~dockerfabric.apiclient.DockerFabricClient` is a client for access to a remote Docker host, which has been
enhanced with some additional functionality. It is a Fabric adaption to
:class:`~dockermap.map.base.DockerClientWrapper` from the Docker-Map_ package, which again is based on docker-py_, the
reference Python client for the `Docker Remote API`_.

:class:`~dockermap.map.base.DockerClientWrapper` wraps some functions of `docker-py`, but most methods of its original
implementation can also be used directly. This is described in more depth in the
:ref:`Docker-Map documentation <dockermap:container_client>`. The following sections focus on the details specific for
Docker-Fabric.


Basic usage
-----------
The constructor of :class:`~dockerfabric.apiclient.DockerFabricClient` accepts the same arguments as the `docker-py`
implementation (``base_url``, ``version``, and ``timeout``), which are passed through. Moreover, ``tunnel_remote_port``
and ``tunnel_local_port`` are available. The following arguments of :class:`~dockerfabric.apiclient.DockerFabricClient`
fall back to Fabric ``env`` variables, if not specified explicitly:

* ``base_url``: ``env.docker_base_url``
* ``version``: ``env.docker_api_version``
* ``timeout``: ``env.docker_timeout``
* ``tunnel_remote_port``: ``env.docker_tunnel_remote_port``
* ``tunnel_local_port``: ``env.docker_tunnel_local_port``

Although instances of :class:`~dockerfabric.apiclient.DockerFabricClient` can
be created directly, it is more practical to do so implicitly by calling :func:`~dockerfabric.apiclient.docker_fabric`
instead:

* If parameters are set up in the Fabric environment, as listed in the :ref:`fabric_env` section, no further
  configuration is necessary.
* More importantly, existing client connections (and possibly tunnels) are cached and reused, similar to Fabric's
  connection caching. Therefore, you do not need to keep global references to the client around.

For example, consider the following task::

    from dockerfabric.api import docker_fabric

    @task
    def sample_task():
        images = docker_fabric().images()
        ...
        containers = docker_fabric().containers(all=True)
        ...


The fist call to ``docker_fabric()`` opens the connection, and although you may choose to reference the client object
with an extra variable, it will not use significantly more time to run ``docker_fabric()`` a second time. This becomes
important especially on tunnelled connections.

New connections are opened for each combination of Fabric's host string and the Docker base URL. Therefore, you can run
the task on multiple machines at once, just as any other Fabric task.


Working with multiple clients
-----------------------------
Whereas ``docker_fabric()`` always opens the connection on the current host (determined by ``env.host_string``), it may
be beneficial to run Docker commands without a ``host_string`` or ``roles`` assignment if

* the set of clients, that are supposed to run container configurations, does not match the role definitions in
  Fabric;
* you do not feel like creating a separate task with host or role lists for each container configuration to be
  launched;
* or the client in some way require different instantiation parameters (e.g. different service URL, tunnel ports, or
  individual timeout settings).

Docker-Fabric enhances the client configuration from Docker-Map_ in
:class:`~dockerfabric.apiclient.DockerClientConfiguration`. Setting any of ``base_url``, ``version``, ``timeout``,
``tunnel_remote_port`` or ``tunnel_local_port`` overrides the global settings from the ``env`` variables mentioned in
the last section. The object is mapped to Fabric's host configurations by the ``fabric_host`` variable.

If stored as a dictionary in ``env.docker_clients``, configurations are used automatically by ``container_fabric()``.


SSH Tunnelling
--------------
Docker is by default configured to only accept connections on a Unix socket. This is good practice for security reasons,
as the socket can be protected with file system permissions, whereas the attack surface with TCP-IP would be larger.
However, it also makes outside access for administrative purposes more difficult.

Fabric's SSH connection can tunnel connections from the local client to the remote host. If the service is
only exposed over a Unix domain socket, the client additionally launches a **socat** process on the remote end for
forwarding traffic between the remote tunnel endpoint and that Unix socket. That way, no permanent reconfiguration of
Docker is necessary.


Tunnel functionality
^^^^^^^^^^^^^^^^^^^^
Without a host connection in Fabric, the client attempts to make all connection locally (i.e. acts just like the
`docker-py` client). With a ``host_string`` set, the :class:`~dockerfabric.apiclient.DockerFabricClient` opens a tunnel
to forward traffic between the local machine and the Docker service on the remote host. Practically, a modified URL
``tcp://127.0.0.1:<local port>`` is passed to `docker-py`, where ``<local port>`` is the specified via
``tunnel_local_port``. There are two tunnel methods, depending on the connection type to Docker:

#. If ``base_url`` indicates a Unix domain socket, i.e. it is prefixed with any ``http+unix:``, ``unix:``, ``/``, or
   if it is left empty, **socat** is started on the remote end and forwards traffic between the remote tunnel endpoint
   and the socket.
#. In other cases of ``base_url``, the client attempts to connect directly through the established tunnel to the
   Docker service on the remote end. The service has to be exposed to the port included in the ``base_url`` or set in
   ``tunnel_remote_port`` or.

As there needs to be a separate local port for every connection, the exact port ``tunnel_local_port`` is only used once
between multiple clients. :class:`~dockerfabric.apiclient.DockerFabricClient` increases this by one for each additional
host. From version 0.1.4, this also works with :ref:`parallel tasks in Fabric <fabric:parallel-execution>`.

Socat options
^^^^^^^^^^^^^
From version 0.2.0, **socat** does not expose a port on the remote end and therefore does not require further
configuration. For information purposes, the client can however be set to echo the command to `stdout` by setting
``env.socat_quiet`` to ``False``.

The utility task ``reset_socat`` removes **socat** processes, in case of occasional re-connection issues. Since
**socat** no longer forks on accepting a connection, this should no longer occur.


Configuration example
---------------------

Single-client configuration
^^^^^^^^^^^^^^^^^^^^^^^^^^^
Consider the following lines in your project's ``fabfile.py``::

    env.docker_tunnel_local_port = 2224
    env.docker_timeout = 20


With this configuration, ``docker_fabric()`` in a task running on each host

#. opens a channel on the existing SSH connection and launches **socat** on the remote, forwarding traffic between
   the remote `stdout` and ``/var/run/docker.sock`` (the default base URL);
#. opens a tunnel through the existing SSH connection on port 2224 (increased by 1 for every additional host);
#. cancels operations that take longer than 20 seconds.

Multi-client configuration
^^^^^^^^^^^^^^^^^^^^^^^^^^
In addition to the previous example, adding the following additional lines in your project's ``fabfile.py``::

    env.docker_clients = {
        'client1': DockerClientConfiguration({
            'fabric_host': 'host1',
            'timeout': 40,  # Host needs longer timeouts than usual.
        }),
        'client2': DockerClientConfiguration({
            'fabric_host': 'host2',
            'interfaces': {
                'private': '10.x.x.11',  # Host will be publishing some ports.
                'public': '178.x.x.11',
            },
        }),
    }

A single client can be instantiated using::

    env.docker_clients['client1'].get_client()

Similar to ``docker_fabric()`` each client per host and service URL is only instantiated once.


Registry connections
--------------------
Docker-Fabric offers the following additional options for configuring registry access from the Docker host to a
registry, as described in the :ref:`fabric_env` section. Those can be either set with keyword arguments at run-time,
or with the environment variables:

* ``username``: ``env.docker_registry_user``
* ``password``: ``env.docker_registry_password``
* ``email``: ``env.docker_registry_mail``
* ``registry``: ``env.docker_registry_repository``
* ``insecure_registry``: ``env.docker_registry_insecure``

Whereas ``env.docker_registry_insecure`` applies to :meth:`~dockerfabric.apiclient.DockerFabricClient.login`,
:meth:`~dockerfabric.apiclient.DockerFabricClient.pull`, and :meth:`~dockerfabric.apiclient.DockerFabricClient.push`,
the others are only evaluated during :meth:`~dockerfabric.apiclient.DockerFabricClient.login`.

.. note:: Before a registry action, the local Docker client uses the `ping` endpoint of the registry to check on the
          connection. This has implications for using HTTPS connections between your Docker host(s) and the registry:
          Although everything is working fine on the Docker command line of the host, your client may reject the
          certificate because it does not trust it. This is very common with self-signed certificates, but can happen
          even with purchased ones. This behavior is defined by `docker-py`.

          There are two methods to circumvent this issue: Either set ``insecure_registry`` (or
          ``env.docker_registry_insecure``) to ``True``; or add the certificate authority that signed the registry's
          certificate to your local trust store.


Docker-Map utilities
--------------------
As it is based on Docker-Map_, Docker-Fabric has also inherited all of its functionality. Regarding container maps,
a few adaptions are described in the section :ref:`containers`. The process of generating a `Dockerfile` and building an
image from that is however very similar to the description in the
:ref:`Docker-Map documentation <dockermap:build_images>`::

    from dockermap.api import DockerFile

    dockerfile = DockerFile('ubuntu', maintainer='ME, me@example.com')
    ...
    docker_fabric().build_from_file(dockerfile, 'new_image')


.. _Docker-Map: https://pypi.python.org/pypi/docker-map
.. _Docker Remote API: https://docs.docker.com/reference/api/docker_remote_api/
.. _docker-py: https://github.com/docker/docker-py
.. _running Docker with HTTPS: https://docs.docker.com/articles/https/
