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
reference to other  configuration variables::

    env.host_root_path = '/var/lib/site'
    env.registry_prefix = 'registry.example.com'
    env.nginx_config_path = 'config/nginx'
    env.app1_config_path = 'config/app1'
    env.app2_config_path = 'config/app2'
    env.app1_data_path = 'data/app1'
    env.app2_data_path = 'data/app2'

    env.container_map = ContainerMap('example_map', {
        'repository': env.registry_prefix,
        'host_root': env.host_root_path,
        'web_server': { # Configure container creation and startup
            'image': 'nginx',
            'binds': {'web_config': 'ro'},
            'uses': 'app_server_socket',
            'attaches': 'web_log',
            'start_options': {
                'port_bindings': {80: 80, 443: 443},
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
            'web_config': '/etc/nginx',
            'web_log': '/var/log/nginx',
            'app_server_socket': '/var/lib/app/socket',
            'app_config': '/var/lib/app/config',
            'app_log': '/var/lib/app/log',
            'app_data': '/var/lib/app/data',
        },
        'host': { # Configure volume paths on the Docker host
            'web_config': env.nginx_config_path,
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

    with ContainerFabric(env.container_map) as c:
        c.create('web_server')
        c.start('web_server')

:class:`~dockerfabric.apiclient.ContainerFabric` calls :func:`~dockerfabric.apiclient.docker_fabric`, and therefore
runs the selected map on each host.

.. note:: It makes sense to link container maps with Fabric's role definitions. This will soon be implemented
          in Docker-Fabric. Until then, if you would like to look up roles of the current host, you can use the
          :func:`~dockerfabric.utils.base.get_current_roles` utility function.

YAML import for container maps
------------------------------
Import of YAML files works identically to :ref:`Docker-Map's implementation <dockermap:container_yaml>`, but with one
more added tag: ``!env``. Where applied, the following string is substituted with the current value of a
corresponding ``env`` variable.

.. note:: It is quite obvious that in this case the order of setting variables is essential. Missing variables lead to
          a ``KeyError`` exception.

In order to make use of the ``!env`` tag, import the module from Docker-Fabric instead of Docker-Map::

    from dockerfabric import yaml

    env.container_map = yaml.load_map_file('/path/to/example_map.yaml', 'example_map')

Where the above-quoted map could be represented like this:

.. code-block:: yaml

   repository: !env registry_prefix
   host_root: /var/lib/site
   web_server:
     image: nginx
     binds: {web_config: ro}
     uses: app_server_socket
     attaches: web_log
     start_options:
       port_bindings: {80: 80, 443: 443}
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
     web_config: /etc/nginx
     web_log: /var/log/nginx
     app_server_socket: /var/lib/app/socket
     app_config: /var/lib/app/config
     app_log: /var/lib/app/log
     app_data: /var/lib/app/data
   host:
     web_config: !env nginx_config_path
     app_config:
       instance1: !env app1_config_path
       instance2: !env app2_config_path
     app_data:
       instance1: !env app1_data_path
       instance2: !env app2_data_path


.. _Docker-Map: https://docker-map.readthedocs.org/
