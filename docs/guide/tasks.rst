.. _tasks:

Utility tasks for Fabric
========================
Included utility tasks perform some basic actions within Docker. When importing them into your ``fabfile.py``, you
might want to assign an alias to the module, for having a clear task namespace::

    import dockerfabric.tasks as docker

Then the following commands work directly from the command line, e.g. ``fab <task name>``. A basic description of
each task is displayed when running ``fab --list`` -- the following sections describe a few further details.

Setup tasks
-----------
Tasks :func:`~dockerfabric.tasks.install_docker`, :func:`~dockerfabric.tasks.build_socat`, and
:func:`~dockerfabric.tasks.fetch_socat`, and :func:`~dockerfabric.tasks.install_socat` are helpers for setting up
new hosts for Fabric with Docker.

* If not already installed, :func:`~dockerfabric.tasks.install_docker` installs the most recent release of Docker
  on the remote host. Furthermore, it assigns the currently signed-in user to the `docker` user group. This is
  required in order for the :ref:`cli` to work. Note that the user needs to create a new session for the
  group assignment to be effective. Fabric provides the function :func:`~fabric.network.disconnect_all` to enforce
  this if necessary.
* Provided that Docker can only be contacted via a Unix socket, :func:`~dockerfabric.tasks.build_socat` is required
  to handle the forwarding from the SSH connection. :func:`~dockerfabric.tasks.install_socat` downloads and compiles
  **socat** from source.
* Once you have a **socat** binary, it can be replicated to other hosts using :func:`~dockerfabric.tasks.fetch_socat`
  and :func:`~dockerfabric.tasks.install_socat`.

.. note:: Currently :func:`~dockerfabric.tasks.install_docker` is targeted to Ubuntu hosts. This will become
          more flexible in future releases.

General purpose tasks
---------------------
**Socat** does not terminate after all connections to the host have been closed. Although this can be changed by setting
``env.socat_fork`` to ``False``, there may be instances where it may be necessary to close the process manually, e.g.
when the ``fork`` setting has just recently been set. The task :func:`~dockerfabric.tasks.reset_socat` finds **socat**'s
process id(s) and sends a `kill` signal.

For configuration between containers and firewalls, the host's IP address can be obtained using the tasks
:func:`~dockerfabric.tasks.get_ip` and :func:`~dockerfabric.tasks.get_ipv6`. Without further arguments it returns
the address of the `docker0` interface. Specifying a different interface is possible via the first argument:

.. code-block:: bash

   fab get_ip:eth0

returns the IPv4 address of the first network adapter. IPv6 addresses can additionally be expanded, e.g.

.. code-block:: bash

   fab get_ipv6:eth0:True

returns the full address instead of the abbreviated version provided by ``ifconfig``.

.. tip:: If you would like to handle this information directly in code, use the utility functions
         :func:`~dockerfabric.utils.net.get_ip4_address` and :func:`~dockerfabric.utils.net.get_ip6_address` instead.


Docker tasks
------------
The following tasks are directly related to Docker and processed by the service on the remote host.

Information tasks
^^^^^^^^^^^^^^^^^
As mentioned in the :ref:`installation_and_configuration` section, :func:`~dockerfabric.tasks.version` provides a
similar output to running ``docker version`` on the command line.

Similarly, :func:`~dockerfabric.tasks.list_images` and :func:`~dockerfabric.tasks.list_containers` print a list of
available images and running containers. The output is slightly different from the corresponding command line's. For
``list_containers``

* Ports and multiple container names (e.g. linking aliases) are broken into multiple lines,
* images are by default shown without their registry prefix (can be changed by passing ``short_image=False``),
* the absolute creation timestamp is printed,
* and by default all containers are shown (can be changed by passing an empty string as the first argument).

In the output of ``list_images``

* parent image ids are shown,
* and also here the absolute creation timestamp is printed.

Container tasks
^^^^^^^^^^^^^^^
As of version 0.3.0, container maps are recommended to be set in ``env.docker_maps`` (as list or single entry) and
multiple clients to be configured in ``env.docker_clients``. In that setup, the lifecycle of containers, including their
dependencies, can be entirely managed from the command line without creating individual tasks for them.
The module :mod:`~dockerfabric.actions` contains the following actions:

* :func:`~dockerfabric.actions.create` - Creates a container and its dependencies.
* :func:`~dockerfabric.actions.start` - Starts a container and its dependencies.
* :func:`~dockerfabric.actions.stop` - Stops a container and its dependents.
* :func:`~dockerfabric.actions.remove` - Removes a container and its dependents.
* :func:`~dockerfabric.actions.startup` - Creates and starts a container and its dependencies.
* :func:`~dockerfabric.actions.shutdown` - Stops and removes a container and its dependents.
* :func:`~dockerfabric.actions.update` - Updates a container and its dependencies. Creates and starts containers as
  necessary.

.. note::

   There is also a generic action :func:`~dockerfabric.actions.perform`. Performs an action on the given container map
   and configuration. There needs to be a matching implementation in the policy class.

Given the lines in ``fabfile.py``::

    from dockerfabric import yaml, actions

    env.docker_maps = yaml.load_map_file('/path/to/example_map.yaml', 'example_map')
    env.docker_clients = yaml.load_clients_file('/path/to/example_clients.yaml')


The web server from the :ref:`yaml-import` example may be started with

.. code-block:: bash

   fab actions.startup:example_map,web_server

runs the web server and its dependencies. The command

.. code-block:: bash

   fab actions.update:example_map,web_server

stops, removes, re-creates, and starts the container if the image as specified in the container configuration (e.g.
``nginx:latest``) has been updated, or mapped volumes virtual filesystems are found to mismatch the dependency
containers' shared volumes.

Maintencance tasks
^^^^^^^^^^^^^^^^^^
The maintenance tasks :func:`~dockerfabric.tasks.cleanup_containers`, :func:`~dockerfabric.tasks.cleanup_images`, and
:func:`~dockerfabric.tasks.remove_all_containers` simply call the corresponding methods of
:class:`~dockerfabric.apiclient.DockerFabricClient`:

* :func:`~dockerfabric.tasks.cleanup_containers` removes all containers that have the `Exited` status;
* :func:`~dockerfabric.tasks.cleanup_images` removes all untagged images, optionally with the argument ``True`` also
  images without a `latest` tag.
* :func:`~dockerfabric.tasks.remove_all_containers` stops and removes all containers from the host.

Image transfer
^^^^^^^^^^^^^^
Especially during the initial deployment you may run into a situation where manual image transfer is necessary. For
example, when you plan to use your own registry, but would like to use your own web server image for a reverse proxy,
the following tasks help to download the image from your build system to the client, and upload it to the production
server:

Use :func:`~dockerfabric.tasks.save_image` with two arguments: Image name or id, and file name. If the file name is
omitted, the image is stored in the current working directory, as ``<image>.tar.gz``. For performance reasons,
:func:`~dockerfabric.tasks.save_image` currently relies on the command line client. The compressed tarball is generated
on the host.

.. code-block:: bash

   fab docker.save_image:new_image.tar.gz

In reverse, :func:`~dockerfabric.tasks.load_image` uploads a local image to the Docker host. In this case the Docker
Remote API is used. It accepts plain and gzip-compressed tarballs. The local image file name is the first argument.
Since the API often times out for larger images (default is 60 seconds), the period is extended temporarily to
120 seconds. This can optionally be adjusted with a second argument, e.g.

.. code-block:: bash

   fab docker.load_image:new_image.tar.gz:600

for an image that might take longer to upload due to a slow connection.
