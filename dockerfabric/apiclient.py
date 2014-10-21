# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import six
from docker import client as docker
from fabric.api import env

from dockermap.map import base, client
from .socat import socat_tunnels
from .tunnel import local_tunnels


DOCKER_LOG_FORMAT = "[{0}] docker: {1}"


class DockerFabricConnections(dict):
    """
    Cache for connections to the Docker Remote API.
    """
    def get_connection(self):
        """
        Create a new connection, or return an existing one from the cache. Uses Fabric's current ``env.host_string``
        and the URL to the Docker service.
        """
        key = env.host_string, env.docker_base_url
        conn = self.get(key)
        if not conn:
            conn = DockerFabricClient()
            self[key] = conn
        return conn


docker_fabric = DockerFabricConnections().get_connection


class DockerFabricClient(base.DockerClientWrapper):
    """
    Docker client for Fabric.

    For functional enhancements to :class:`docker.client.Client`, see :class:`~dockermap.map.base.DockerClientWrapper`.
    This implementation only adds the possibility to build a tunnel through the current SSH connection and adds
    Fabric-usual logging.

    If a unix socket is used, `socat` will be started on the remote side to redirect it to a TCP port.

    :param base_url: URL to connect to; if not set, will try to use ``env.docker_base_url``.
    :type base_url: unicode
    :param version: API version; if not set, will try to use ``env.docker_api_version``; otherwise defaults to
     :const:`~docker.client.DEFAULT_DOCKER_API_VERSION`.
    :type version: unicode
    :param timeout: Client timeout for Docker; if not set, will try to use ``env.docker_timeout``; otherwise defaults to
     :const:`~docker.client.DEFAULT_TIMEOUT_SECONDS`.
    :type timeout: int
    :param tunnel_remote_port: Optional, for SSH tunneling: Port to open on the remote end for the tunnel; if set to
     ``None``, will try to use ``env.docker_tunnel_remote_port``; otherwise defaults to ``None`` for no tunnel.
    :type tunnel_remote_port: int
    :param tunnel_local_port: Optional, for SSH tunneling: Port to open towards the local end for the tunnel; if set to
     ``None``, will try to use ``env.docker_tunnel_local_port``; otherwise defaults to the value of ``tunnel_remote_port``.
    :type tunnel_local_port: int
    :param kwargs: Additional kwargs for :class:`docker.client.Client`
    """
    def __init__(self, base_url=None, version=None, timeout=None, tunnel_remote_port=None, tunnel_local_port=None, **kwargs):
        remote_port = tunnel_remote_port or env.get('docker_tunnel_remote_port')
        if not tunnel_local_port:
            local_port = env.get('docker_tunnel_local_port', remote_port)
            env.docker_tunnel_local_port = int(local_port) + 1
        else:
            local_port = tunnel_local_port
        url = base_url or env.get('docker_base_url')
        api_version = version or env.get('docker_api_version', docker.DEFAULT_DOCKER_API_VERSION)
        client_timeout = timeout or env.get('docker_timeout', docker.DEFAULT_TIMEOUT_SECONDS)
        if url is not None and remote_port is not None:
            p1, __, p2 = url.partition(':')
            remote_host = p2 or p1
            if url.startswith('http+unix:') or url.startswith('unix:') or url.startswith('/'):
                self._tunnel = socat_tunnels[(remote_host, remote_port, local_port)]
            else:
                self._tunnel = local_tunnels[(remote_port, remote_host, local_port)]
            conn_url = ':'.join(('tcp://127.0.0.1', six.text_type(local_port)))
        else:
            self._socket_tunnel = None
            conn_url = url
        super(DockerFabricClient, self).__init__(base_url=conn_url, version=api_version, timeout=client_timeout, **kwargs)

    def push_log(self, info):
        """
        Prints the log as usual for fabric output, enhanced with the prefix "docker".

        :param info: Log output.
        :type info: unicode
        """
        print(DOCKER_LOG_FORMAT.format(env.host_string, info))

    def close(self):
        """
        Closes the connection and any tunnels created for it.
        """
        try:
            super(DockerFabricClient, self).close()
        finally:
            if self._tunnel is not None:
                self._tunnel.close()

    def build(self, tag, **kwargs):
        """
        Identical to :func:`dockermap.map.base.DockerClientWrapper.build` with additional logging.
        """
        self.push_log("Building image '{0}'.".format(tag))
        return super(DockerFabricClient, self).build(tag, **kwargs)

    def create_container(self, image, name=None, **kwargs):
        """
        Identical to :func:`dockermap.map.base.DockerClientWrapper.create_container` with additional logging.
        """
        name_str = " '{0}'".format(name) if name else ""
        self.push_log("Creating container{0} from image '{1}'.".format(name_str, image))
        return super(DockerFabricClient, self).create_container(image, name=name, **kwargs)

    def copy_resource(self, container, resource, local_filename):
        """
        Identical to :func:`dockermap.map.base.DockerClientWrapper.copy_resource` with additional logging.
        """
        self.push_log("Receiving tarball for resource '{0}:{1}' and storing as {2}".format(container, resource, local_filename))
        super(DockerFabricClient, self).copy_resource(container, resource, local_filename)

    def cleanup_containers(self):
        """
        Identical to :func:`dockermap.map.base.DockerClientWrapper.copy_resource` with additional logging.
        """
        self.push_log("Generating list of stopped containers.")
        super(DockerFabricClient, self).cleanup_containers()

    def cleanup_images(self, remove_old=False):
        """
        Identical to :func:`dockermap.map.base.DockerClientWrapper.copy_resource` with additional logging.
        """
        self.push_log("Checking images for dependent images and containers.")
        super(DockerFabricClient, self).cleanup_images(remove_old)

    def get_container_names(self):
        """
        Identical to :func:`dockermap.map.base.DockerClientWrapper.copy_resource` with additional logging.
        """
        self.push_log("Fetching container list.")
        return super(DockerFabricClient, self).get_container_names()

    def get_image_tags(self):
        """
        Identical to :func:`dockermap.map.base.DockerClientWrapper.copy_resource` with additional logging.
        """
        self.push_log("Fetching image list.")
        return super(DockerFabricClient, self).get_image_tags()

    def import_image(self, image, tag='latest', **kwargs):
        """
        Identical to :func:`dockermap.map.base.DockerClientWrapper.copy_resource` with additional logging.
        """
        self.push_log("Fetching image '{0}' from registry.".format(image))
        return super(DockerFabricClient, self).import_image(image=image, tag=tag, **kwargs)

    def login(self, **kwargs):
        """
        Identical to :func:`dockermap.map.base.DockerClientWrapper.login` with two enhancements:

        * additional logging;
        * login parameters can be passed through ``kwargs``, or set as default using the following ``env``
          variables:

          * ``env.docker_registry_user`` (kwarg: ``username``),
          * ``env.docker_registry_password`` (kwarg: ``password``),
          * ``env.docker_registry_mail`` (kwarg: ``email``),
          * ``env.docker_registry_repository`` (kwarg: ``registry``),
          * ``env.docker_registry_insecure`` (kwarg: ``insecure_registry``).
        """
        c_user = kwargs.pop('username', env.get('docker_registry_user'))
        c_pass = kwargs.pop('password', env.get('docker_registry_password'))
        c_mail = kwargs.pop('email', env.get('docker_registry_mail'))
        c_registry = kwargs.pop('registry', env.get('docker_registry_repository'))
        c_insecure = kwargs.pop('insecure_registry', env.get('docker_registry_insecure'))
        if super(DockerFabricClient, self).login(c_user, password=c_pass, email=c_mail, registry=c_registry,
                                                 insecure_registry=c_insecure, **kwargs):
            self.push_log("Login at registry '{0}' succeeded.".format(c_registry))
            return True
        self.push_log("Login at registry '{0}' failed.".format(c_registry))
        return False

    def pull(self, repository, tag=None, stream=True, **kwargs):
        """
        Identical to :func:`dockermap.map.base.DockerClientWrapper.pull` with two enhancements:

        * additional logging;
        * the ``insecure_registry`` flag can be passed through ``kwargs``, or set as default using
          ``env.docker_registry_insecure``.
        """
        c_insecure = kwargs.pop('insecure_registry', env.get('docker_registry_insecure'))
        return super(DockerFabricClient, self).pull(repository, tag=tag, stream=stream, insecure_registry=c_insecure,
                                                    **kwargs)

    def push(self, repository, stream=True, **kwargs):
        """
        Identical to :func:`dockermap.map.base.DockerClientWrapper.push` with two enhancements:

        * additional logging;
        * the ``insecure_registry`` flag can be passed through ``kwargs``, or set as default using
          ``env.docker_registry_insecure``.
        """
        c_insecure = kwargs.pop('insecure_registry', env.get('docker_registry_insecure'))
        return super(DockerFabricClient, self).push(repository, stream=stream, insecure_registry=c_insecure, **kwargs)

    def remove_all_containers(self):
        """
        Identical to :func:`dockermap.map.base.DockerClientWrapper.remove_all_containers` with additional logging.
        """
        self.push_log("Fetching container list.")
        super(DockerFabricClient, self).remove_all_containers()

    def remove_container(self, container, **kwargs):
        """
        Identical to :func:`docker.client.Client.remove_container` with additional logging.
        """
        self.push_log("Removing container '{0}'.".format(container))
        super(DockerFabricClient, self).remove_container(container, **kwargs)

    def remove_image(self, image, **kwargs):
        """
        Identical to :func:`docker.client.Client.remove_image` with additional logging.
        """
        self.push_log("Removing image '{0}'.".format(image))
        super(DockerFabricClient, self).remove_image(image, **kwargs)

    def save_image(self, image, local_filename):
        """
        Identical to :func:`dockermap.map.base.DockerClientWrapper.save_image` with additional logging.
        """
        self.push_log("Receiving tarball for image '{0}' and storing as '{1}'".format(image, local_filename))
        super(DockerFabricClient, self).save_image(image, local_filename)

    def start(self, container, **kwargs):
        """
        Identical to :func:`dockermap.map.base.DockerClientWrapper.start` with additional logging.
        """
        self.push_log("Starting container '{0}'.".format(container))
        super(DockerFabricClient, self).start(container, **kwargs)

    def stop(self, container, **kwargs):
        """
        Identical to :func:`docker.client.Client.stop` with additional logging.
        """
        self.push_log("Stopping container '{0}'.".format(container))
        super(DockerFabricClient, self).stop(container, **kwargs)

    def wait(self, container):
        """
        Identical to :func:`docker.client.Client.wait` with additional logging.
        """
        self.push_log("Waiting for container '{0}'.".format(container))
        super(DockerFabricClient, self).wait(container)


class ContainerFabric(client.MappingDockerClient):
    """
    Convenience class for using a :class:`~dockermap.map.container.ContainerMap` on a :class:`DockerFabricClient`.

    :param container_map: Container map.
    :type container_map: dockermap.map.container.ContainerMap
    """
    def __init__(self, container_map):
        super(ContainerFabric, self).__init__(container_map, docker_fabric())

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass
