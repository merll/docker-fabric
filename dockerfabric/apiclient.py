# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging
from fabric.api import env, sudo
from fabric.utils import puts, fastprint, error

from dockermap.client.base import LOG_PROGRESS_FORMAT, DockerStatusError
from dockermap.api import DockerClientWrapper, MappingDockerClient
from .base import DockerConnectionDict, get_local_port, FabricClientConfiguration, FabricContainerClient
from .socat import socat_tunnels
from .tunnel import local_tunnels


DEFAULT_TCP_HOST = 'tcp://127.0.0.1'
DEFAULT_SOCKET = '/var/run/docker.sock'
progress_fmt = LOG_PROGRESS_FORMAT.format


def _get_port_number(expr, port_loc):
    try:
        return int(expr)
    except TypeError:
        raise ValueError("Missing or invalid {0} port ({1}).".format(port_loc, expr))


def _get_socat_tunnel(address, local_port):
    init_local_port = _get_port_number(local_port, 'local')
    tunnel_local_port = get_local_port(init_local_port)
    socat_tunnel = socat_tunnels[(address, tunnel_local_port)]
    return '{0}:{1}'.format(DEFAULT_TCP_HOST, socat_tunnel.bind_port), socat_tunnel


def _get_local_tunnel(address, remote_port, local_port):
    host_port = address.partition('/')[0]
    host, __, port = host_port.partition(':')
    service_remote_port = _get_port_number(port or remote_port, 'remote')
    init_local_port = _get_port_number(local_port or port or remote_port, 'local')
    local_tunnel = local_tunnels[(host, service_remote_port, 'localhost', init_local_port)]
    return '{0}:{1}'.format(DEFAULT_TCP_HOST, local_tunnel.bind_port), local_tunnel


def _get_connection_args(base_url, remote_port, local_port):
    if env.host_string:
        if base_url:
            proto_idx = base_url.find(':/')
            if proto_idx >= 0:
                proto = base_url[:proto_idx]
                address = base_url[proto_idx + 2:]
                if proto in ('http+unix', 'unix'):
                    if address[:3] == '//':
                        address = address[1:]
                    elif address[0] != '/':
                        address = ''.join(('/', address))
                    return _get_socat_tunnel(address, local_port)
                return _get_local_tunnel(address.lstrip('/'), remote_port, local_port)
            elif base_url[0] == '/':
                return _get_socat_tunnel(base_url, local_port)
            return _get_local_tunnel(base_url, remote_port, local_port)
        return _get_socat_tunnel(DEFAULT_SOCKET, local_port)
    return base_url, None


class DockerFabricClient(DockerClientWrapper):
    """
    Docker client for Fabric.

    For functional enhancements to :class:`docker.client.Client`, see :class:`~dockermap.map.base.DockerClientWrapper`.
    This implementation only adds the possibility to build a tunnel through the current SSH connection and adds
    Fabric-usual logging.

    If a unix socket is used, `socat` will be started on the remote side to redirect it to a TCP port.

    :param base_url: URL to connect to; if not set, will refer to ``env.docker_base_url`` or use ``None``, which by
     default attempts a connection on a Unix socket at ``/var/run/docker.sock``.
    :type base_url: unicode
    :param version: API version; if not set, will try to use ``env.docker_api_version``; otherwise defaults to
     :const:`~docker.client.DEFAULT_DOCKER_API_VERSION`.
    :type version: unicode
    :param timeout: Client timeout for Docker; if not set, will try to use ``env.docker_timeout``; otherwise defaults to
     :const:`~docker.client.DEFAULT_TIMEOUT_SECONDS`.
    :type timeout: int
    :param tunnel_remote_port: Optional, port of the remote service; if port is included in ``base_url``, the latter
     is preferred. If not set, will try to use ``env.docker_tunnel_remote_port``; otherwise defaults to ``None``.
    :type tunnel_remote_port: int
    :param tunnel_local_port: Optional, for SSH tunneling: Port to open towards the local end for the tunnel; if not
     provided, will try to use ``env.docker_tunnel_local_port``; otherwise defaults to the value of
     ``tunnel_remote_port`` or ``None`` for direct connections without an SSH tunnel.
    :type tunnel_local_port: int
    :param kwargs: Additional kwargs for :class:`docker.client.Client`
    """
    def __init__(self, base_url=None, version=None, timeout=None, tunnel_remote_port=None, tunnel_local_port=None,
                 **kwargs):
        url = base_url or env.get('docker_base_url')
        api_version = version or env.get('docker_api_version')
        client_timeout = timeout or env.get('docker_timeout')
        remote_port = tunnel_remote_port or env.get('docker_tunnel_remote_port')
        local_port = tunnel_local_port or env.get('docker_tunnel_local_port', remote_port)
        conn_url, self._tunnel = _get_connection_args(url, remote_port, local_port)
        super(DockerFabricClient, self).__init__(base_url=conn_url, version=api_version, timeout=client_timeout,
                                                 **kwargs)

    def push_log(self, info, level=logging.INFO, *args, **kwargs):
        """
        Prints the log as usual for fabric output, enhanced with the prefix "docker".

        :param info: Log output.
        :type info: unicode
        """
        if args:
            msg = info % args
        else:
            msg = info
        try:
            puts('docker: {0}'.format(msg))
        except UnicodeDecodeError:
            puts('docker: -- non-printable output --')

    def push_progress(self, status, object_id, progress):
        """
        Prints progress information.

        :param status: Status text.
        :type status: unicode
        :param object_id: Object that the progress is reported on.
        :type object_id: unicode
        :param progress: Progress bar.
        :type progress: unicode
        """
        fastprint(progress_fmt(status, object_id, progress), end='\n')

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
        Identical to :meth:`dockermap.map.base.DockerClientWrapper.build` with additional logging.
        """
        kwargs['raise_on_error'] = True
        self.push_log("Building image '{0}'.".format(tag))
        try:
            return super(DockerFabricClient, self).build(tag, **kwargs)
        except DockerStatusError as e:
            error(e.message)

    def create_container(self, image, name=None, **kwargs):
        """
        Identical to :meth:`dockermap.map.base.DockerClientWrapper.create_container` with additional logging.
        """
        name_str = " '{0}'".format(name) if name else ""
        self.push_log("Creating container{0} from image '{1}'.".format(name_str, image))
        return super(DockerFabricClient, self).create_container(image, name=name, **kwargs)

    def copy_resource(self, container, resource, local_filename):
        """
        Identical to :meth:`dockermap.map.base.DockerClientWrapper.copy_resource` with additional logging.
        """
        self.push_log("Receiving tarball for resource '{0}:{1}' and storing as {2}".format(container, resource, local_filename))
        super(DockerFabricClient, self).copy_resource(container, resource, local_filename)

    def cleanup_containers(self, include_initial=False, exclude=None, raise_on_error=False):
        """
        Identical to :meth:`dockermap.map.base.DockerClientWrapper.cleanup_containers` with additional logging.
        """
        self.push_log("Generating list of stopped containers.")
        super(DockerFabricClient, self).cleanup_containers(include_initial=include_initial, exclude=exclude,
                                                           raise_on_error=raise_on_error)

    def cleanup_images(self, remove_old=False, keep_tags=None, raise_on_error=False):
        """
        Identical to :meth:`dockermap.map.base.DockerClientWrapper.cleanup_images` with additional logging.
        """
        self.push_log("Checking images for dependent images and containers.")
        super(DockerFabricClient, self).cleanup_images(remove_old=remove_old, keep_tags=keep_tags,
                                                       raise_on_error=raise_on_error)

    def get_container_names(self):
        """
        Identical to :meth:`dockermap.map.base.DockerClientWrapper.get_container_names` with additional logging.
        """
        self.push_log("Fetching container list.")
        return super(DockerFabricClient, self).get_container_names()

    def get_image_tags(self):
        """
        Identical to :meth:`dockermap.map.base.DockerClientWrapper.get_image_tags` with additional logging.
        """
        self.push_log("Fetching image list.")
        return super(DockerFabricClient, self).get_image_tags()

    def import_image(self, image=None, tag='latest', **kwargs):
        """
        Identical to :meth:`docker.client.Client.import_image` with additional logging.
        """
        self.push_log("Fetching image '{0}' from registry.".format(image))
        return super(DockerFabricClient, self).import_image(image=image, tag=tag, **kwargs)

    def login(self, **kwargs):
        """
        Identical to :meth:`dockermap.map.base.DockerClientWrapper.login` with two enhancements:

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
        Identical to :meth:`dockermap.map.base.DockerClientWrapper.pull` with two enhancements:

        * additional logging;
        * the ``insecure_registry`` flag can be passed through ``kwargs``, or set as default using
          ``env.docker_registry_insecure``.
        """
        c_insecure = kwargs.pop('insecure_registry', env.get('docker_registry_insecure'))
        if 'raise_on_error' not in kwargs:
            kwargs['raise_on_error'] = True
        try:
            return super(DockerFabricClient, self).pull(repository, tag=tag, stream=stream,
                                                        insecure_registry=c_insecure, **kwargs)
        except DockerStatusError as e:
            error(e.message)

    def push(self, repository, stream=True, **kwargs):
        """
        Identical to :meth:`dockermap.map.base.DockerClientWrapper.push` with two enhancements:

        * additional logging;
        * the ``insecure_registry`` flag can be passed through ``kwargs``, or set as default using
          ``env.docker_registry_insecure``.
        """
        c_insecure = kwargs.pop('insecure_registry', env.get('docker_registry_insecure'))
        kwargs['raise_on_error'] = True
        try:
            return super(DockerFabricClient, self).push(repository, stream=stream, insecure_registry=c_insecure,
                                                        **kwargs)
        except DockerStatusError as e:
            error(e.message)

    def restart(self, container, **kwargs):
        """
        Identical to :meth:`docker.client.Client.restart` with additional logging.
        """
        self.push_log("Restarting container '{0}'.".format(container))
        super(DockerFabricClient, self).restart(container, **kwargs)

    def remove_all_containers(self):
        """
        Identical to :meth:`dockermap.map.base.DockerClientWrapper.remove_all_containers` with additional logging.
        """
        self.push_log("Fetching container list.")
        super(DockerFabricClient, self).remove_all_containers()

    def remove_container(self, container, raise_on_error=False, **kwargs):
        """
        Identical to :meth:`dockermap.map.base.DockerClientWrapper.remove_container` with additional logging.
        """
        self.push_log("Removing container '{0}'.".format(container))
        super(DockerFabricClient, self).remove_container(container, raise_on_error=raise_on_error, **kwargs)

    def remove_image(self, image, **kwargs):
        """
        Identical to :meth:`docker.client.Client.remove_image` with additional logging.
        """
        self.push_log("Removing image '{0}'.".format(image))
        super(DockerFabricClient, self).remove_image(image, **kwargs)

    def save_image(self, image, local_filename):
        """
        Identical to :meth:`dockermap.map.base.DockerClientWrapper.save_image` with additional logging.
        """
        self.push_log("Receiving tarball for image '{0}' and storing as '{1}'".format(image, local_filename))
        super(DockerFabricClient, self).save_image(image, local_filename)

    def start(self, container, **kwargs):
        """
        Identical to :meth:`docker.client.Client.start` with additional logging.
        """
        self.push_log("Starting container '{0}'.".format(container))
        super(DockerFabricClient, self).start(container, **kwargs)

    def stop(self, container, **kwargs):
        """
        Identical to :meth:`docker.client.Client.stop` with additional logging.
        """
        self.push_log("Stopping container '{0}'.".format(container))
        super(DockerFabricClient, self).stop(container, **kwargs)

    def wait(self, container, **kwargs):
        """
        Identical to :meth:`docker.client.Client.wait` with additional logging.
        """
        self.push_log("Waiting for container '{0}'.".format(container))
        super(DockerFabricClient, self).wait(container, **kwargs)

    def run_cmd(self, command):
        sudo(command)


class DockerFabricApiConnections(DockerConnectionDict):
    client_class = DockerFabricClient


# Still defined here for backwards compatibility.
docker_fabric = DockerFabricApiConnections().get_connection


class DockerClientConfiguration(FabricClientConfiguration):
    init_kwargs = FabricClientConfiguration.init_kwargs + ('tunnel_remote_port', 'tunnel_local_port')
    client_constructor = docker_fabric


class ContainerApiFabricClient(FabricContainerClient):
    configuration_class = DockerClientConfiguration


# Still defined here for backwards compatibility.
container_fabric = ContainerApiFabricClient
