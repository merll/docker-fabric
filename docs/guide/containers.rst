.. _containers:

Fabric with Container maps
==========================
Using :func:`~dockerfabric.apiclient.docker_fabric`, the standard API to Docker is accessible in a similar way to
other Fabric commands. With Docker-Map_, the API has been enhanced with a set of utilities to configure containers
and their dependencies.

The configuration is in full discussed in the :ref:`Docker-Map configuration <dockermap:container_maps>`, along with
examples. This section explains how to apply this to Docker-Fabric.

Managing containers
-------------------
In order to have the map available in your Fabric project, it is practical to store a reference in the global
``env`` object. The :ref:`example from Docker-Map <dockermap:container_map_example>` could be initialized with
reference to other configuration variables::

    env.host_root_path = '/var/lib/site'
    env.registry_prefix = 'registry.example.com'
    env.nginx_config_path = 'config/nginx'
    env.app1_config_path = 'config/app1'
    env.app2_config_path = 'config/app2'
    env.app1_data_path = 'data/app1'
    env.app2_data_path = 'data/app2'

    env.docker_maps = ContainerMap('example_map', {
        'repository': env.registry_prefix,
        'host_root': env.host_root_path,
        'web_server': { # Configure container creation and startup
            'image': 'nginx',
            'binds': {'/etc/nginx': ('env.nginx_config_path', 'ro')},
            'uses': 'app_server_socket',
            'attaches': 'web_log',
            'exposes': {
                80: 80,
                443: 443,
            },
        },
        'app_server': {
            'image': 'app',
            'instances': ('instance1', 'instance2'),
            'binds': (
                {'app_config': 'ro'},
                'app_data',
            ),
            'attaches': ('app_log', 'app_server_socket'),
            'user': 2000,
            'permissions': 'u=rwX,g=rX,o=',
        },
        'volumes': { # Configure volume paths inside containers
            'web_log': '/var/log/nginx',
            'app_server_socket': '/var/lib/app/socket',
            'app_config': '/var/lib/app/config',
            'app_log': '/var/lib/app/log',
            'app_data': '/var/lib/app/data',
        },
        'host': { # Configure volume paths on the Docker host
            'app_config': {
                'instance1': env.app1_config_path,
                'instance2': env.app2_config_path,
            },
            'app_data': {
                'instance1': env.app1_data_path,
                'instance2': env.app2_data_path,
            },
        },
    })

In order to use this configuration set, create a :class:`~dockerfabric.apiclient.ContainerFabric` instance from this
map. For example, in order to launch the web server and all dependencies, run::

    from dockerfabric.apiclient import container_fabric

    container_fabric().startup('web_server')

:class:`~dockerfabric.apiclient.ContainerFabric` (aliased with ``container_fabric()``) calls
:func:`~dockerfabric.apiclient.docker_fabric` with the host strings on demand, and therefore runs the selected map on
each host where required.

``env.docker_maps`` can store one container map, or a list / tuple of multiple container maps. You can also store host
definitions in any variable you like and pass them to ``container_fabric``::

    container_fabric(env.container_maps)

Multi-client configurations are automatically considered when stored in ``env.docker_clients``, but can also be passed
through a variable::

    container_fabric(maps=custom_maps, clients=custom_clients)

.. _yaml-import:

YAML import
-----------
Import of YAML files works identically to :ref:`Docker-Map's implementation <dockermap:container_yaml>`, but with one
more added tag: ``!env``. Where applied, the following string is substituted with the current value of a
corresponding ``env`` variable.

When using the ``!env`` tag, the order of setting variables is relevant, since values are substituted at the time the
YAML file is read. For cases where this is impractical some configuration elements support a 'lazy' behavior, i.e. they
are not resolved to their actual values until the first attempt to access them. In order to use that, just apply
``!env_lazy`` in place of ``!env``. For example volume paths and host ports can be assigned with this tag instead. A
full list of variables supporting the late value resolution is maintained in the
:ref:`Docker-Map documentation <dockermap:container_lazy_availability>`.

.. note:: If the variable is still missing at the time it is needed, a ``KeyError`` exception is raised.

In order to make use of the ``!env`` and ``!env_lazy`` tag, import the module from Docker-Fabric instead of Docker-Map::

    from dockerfabric import yaml

    env.docker_maps = yaml.load_map_file('/path/to/example_map.yaml', 'example_map')
    env.docker_clients = yaml.load_clients_file('/path/to/example_clients.yaml')

One more difference to the Docker-Map ``yaml`` module is that :func:`load_clients_file` creates object instances of
:func:`~dockerfabric.apiclient.DockerClientConfiguration`. The latter consider specific settings as the tunnel ports,
which are not part of Docker-Map.

Container map
^^^^^^^^^^^^^
In the file ``example_map.yaml``, the above-quoted map could be represented like this:

.. code-block:: yaml

   repository: !env registry_prefix
   host_root: /var/lib/site
   web_server:
     image: nginx
     binds:
       /etc/nginx:
       - !env nginx_config_path
       - ro
     uses: app_server_socket
     attaches: web_log
     exposes:
       80: 80
       443: 443
   app_server:
     image: app
     instances:
     - instance1
     - instance2
     binds:
     - app_config: ro
     - app_data:
     attaches:
     - app_log
     - app_server_socket
     user: 2000
     permissions: u=rwX,g=rX,o=
   volumes:
     web_log: /var/log/nginx
     app_server_socket: /var/lib/app/socket
     app_config: /var/lib/app/config
     app_log: /var/lib/app/log
     app_data: /var/lib/app/data
   host:
     app_config:
       instance1: !env app1_config_path
       instance2: !env app2_config_path
     app_data:
       instance1: !env app1_data_path
       instance2: !env app2_data_path


Client configurations
^^^^^^^^^^^^^^^^^^^^^
With some modifications, this map could also run a setup on multiple hosts, for example one web server running as
reverse proxy for multiple identical app servers::

    env.docker_maps.update(
        web_server={
            'clients': 'web',
            'uses': [],  # No longer look for a socket
        },
        app_server={
            'clients': ('apps1', 'apps2', 'apps3'),
            'attaches': 'app_log',  # No longer create a socket
            'exposes': [(8443, 8443, 'private')],  # Expose a TCP port on 8443 of the private network interface
        }
    )

The modifications could of course have been included in the aforementioned map right away. Moreover, all of this has to
be set up in the web server's and app servers' configuration accordingly.

A client configuration in ``example_clients.yaml`` could look like this:

.. code-block:: yaml

   web:
     fabric_host: web_host  # Set the Fabric host here.
   apps1:
     fabric_host: app_host1
     interfaces:
       private: 10.x.x.21   # Provide the individual IP address for each host.
   apps2:
     fabric_host: app_host2
     interfaces:
       private: 10.x.x.22
   apps3:
     fabric_host: app_host3
     interfaces:
       private: 10.x.x.23


Since there is no dependency indicated by the configuration between the web and app servers, two startup commands are
required; still they will connect to each host as necessary::

    with container_fabric() as cf:
        cf.startup('web_server')
        cf.startup('app_server')

In addition to creating and starting the containers, ports will be bound to each private network adapter individually.

.. _Docker-Map: https://docker-map.readthedocs.org/
