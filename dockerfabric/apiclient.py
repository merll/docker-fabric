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
    def get_connection(self):
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

    For functional enhancements to :class:`docker.client.Client`, see :class:`.client.DockerClientWrapper`.
    This implementation only adds the possibility to build a tunnel through the current SSH connection and adds
    Fabric-usual logging.

    If a unix socket is used, `socat` will be started on the remote side to redirect it to a TCP port.

    :param base_url: URL to connect to; if not set, will try to use `env.docker_base_url`.
    :type base_url: unicode
    :param version: API version; if not set, will try to use `env.docker_api_version`; otherwise defaults to
     :const:`docker.client.DEFAULT_DOCKER_API_VERSION`.
    :param version: unicode
    :param timeout: Client timeout for Docker; if not set, will try to use `env.docker_timeout`; otherwise defaults to
     :const:`docker.client.DEFAULT_TIMEOUT_SECONDS`.
    :type timeout: int
    :param tunnel_remote_port: Optional, for SSH tunneling: Port to open on the remote end for the tunnel; if set to
     `None`, will try to use `env.docker_tunnel_remote_port`; otherwise defaults to `None` for no tunnel.
    :type tunnel_remote_port: int
    :param tunnel_local_port: Optional, for SSH tunneling: Port to open towards the local end for the tunnel; if set to
     `None`, will try to use `env.docker_tunnel_local_port`; otherwise defaults to the value of `tunnel_remote_port`.
    :type tunnel_local_port: int
    :param kwargs: Additional kwargs for :class:`docker.client.Client`
    """
    def __init__(self, base_url=None, version=None, timeout=None, tunnel_remote_port=None, tunnel_local_port=None, **kwargs):
        remote_port = tunnel_remote_port or env.get('docker_tunnel_remote_port')
        local_port = tunnel_local_port or env.get('docker_tunnel_local_port', remote_port)
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
        self.push_log("Building image '{0}'.".format(tag))
        return super(DockerFabricClient, self).build(tag, **kwargs)

    def create_container(self, image, name=None, **kwargs):
        name_str = " '{0}'".format(name) if name else ""
        self.push_log("Creating container{0} from image '{1}'.".format(name_str, image))
        return super(DockerFabricClient, self).create_container(image, name=name, **kwargs)

    def copy_resource(self, container, resource, local_filename):
        self.push_log("Receiving tarball for resource '{0}:{1}' and storing as {2}".format(container, resource, local_filename))
        super(DockerFabricClient, self).copy_resource(container, resource, local_filename)

    def cleanup_containers(self):
        self.push_log("Generating list of stopped containers.")
        super(DockerFabricClient, self).cleanup_containers()

    def cleanup_images(self):
        self.push_log("Checking images for dependent images and containers.")
        super(DockerFabricClient, self).cleanup_images()

    def get_container_names(self):
        self.push_log("Fetching container list.")
        return super(DockerFabricClient, self).get_container_names()

    def get_image_tags(self):
        self.push_log("Fetching image list.")
        return super(DockerFabricClient, self).get_image_tags()

    def import_image(self, image, tag='latest', **kwargs):
        self.push_log("Fetching image '{0}' from registry.".format(image))
        return super(DockerFabricClient, self).import_image(image=image, tag=tag, **kwargs)

    def login(self, username=None, password=None, email=None, registry=None, reauth=False):
        c_user = username or env.get('docker_registry_user')
        c_pass = password or env.get('docker_registry_password')
        c_mail = email or env.get('docker_registry_mail')
        c_registry = registry or env.get('docker_registry_repository')
        registry_url = 'https://{0}'.format(c_registry)
        result = super(DockerFabricClient, self).login(c_user, c_pass, c_mail, registry_url, reauth=reauth)
        if result.get('Status') == 'Login Succeeded':
            self.push_log("Login at registry '{0}' succeeded.".format(c_registry))
            return True
        self.push_log("Login at registry '{0}' failed.".format(c_registry))
        return False

    def remove_all_containers(self):
        self.push_log("Fetching container list.")
        super(DockerFabricClient, self).remove_all_containers()

    def remove_container(self, container, **kwargs):
        self.push_log("Removing container '{0}'.".format(container))
        super(DockerFabricClient, self).remove_container(container, **kwargs)

    def remove_image(self, image, **kwargs):
        self.push_log("Removing image '{0}'.".format(image))
        super(DockerFabricClient, self).remove_image(image, **kwargs)

    def save_image(self, image, local_filename):
        self.push_log("Receiving tarball for image '{0}' and storing as '{1}'".format(image, local_filename))
        super(DockerFabricClient, self).save_image(image, local_filename)

    def start(self, container, **kwargs):
        self.push_log("Starting container '{0}'.".format(container))
        super(DockerFabricClient, self).start(container, **kwargs)

    def stop(self, container, **kwargs):
        self.push_log("Stopping container '{0}'.".format(container))
        super(DockerFabricClient, self).stop(container, **kwargs)

    def wait(self, container):
        self.push_log("Waiting for container '{0}'.".format(container))
        super(DockerFabricClient, self).wait(container)


class ContainerFabric(client.MappingDockerClient):
    def __init__(self, container_map):
        super(ContainerFabric, self).__init__(container_map, docker_fabric())

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass
