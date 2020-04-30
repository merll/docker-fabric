# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os
import posixpath

from dockermap.api import USE_HC_MERGE
from dockermap.client.cli import (DockerCommandLineOutput, parse_containers_output, parse_inspect_output,
                                  parse_images_output, parse_version_output, parse_top_output, parse_networks_output,
                                  parse_volumes_output, parse_info_output)
from dockermap.client.docker_util import DockerUtilityMixin
from dockermap.map.config.client import ClientConfiguration
from dockermap.shortcuts import chmod, chown, targz, mkdir

from .base import FabricContainerClient, set_registry_config_kwargs
from .utils.containers import temp_container
from .utils.files import temp_dir, is_directory


def _find_image_id(output):
    for line in reversed(output.splitlines()):
        if line and line.startswith('Successfully built '):
            return line[19:]  # Remove prefix
    return None


class DockerCliClient(DockerUtilityMixin):
    """
    Docker client for Fabric using the command line interface on a remote host.

    :param connection: Fabric connection.
    :type connection: fabric.connection.Connection
    :param cmd_prefix: Custom prefix to prepend to the Docker command line.
    :type cmd_prefix: unicode | str
    :param default_bin: Docker binary to use. If not set, uses ``docker``.
    :type default_bin: unicode | str
    :param base_url: URL to connect to; if not set, will refer to ``env.docker_base_url`` or use ``None``, which by
     default attempts a connection on a Unix socket at ``/var/run/docker.sock``.
    :type base_url: unicode | str
    :param tls: Whether to use TLS on the connection to the Docker service.
    :type tls: bool
    :param use_sudo: Whether to use ``sudo`` when performing Docker commands.
    :type use_sudo: bool
    :param debug: If set to ``True``, echoes each command and its console output. Some commands are echoed either way
     for some feedback.
    :type debug: bool
    """
    def __init__(self, connection, cmd_prefix=None, default_bin=None, base_url=None, tls=None, use_sudo=None,
                 debug=None):
        super(DockerCliClient, self).__init__()
        self.connection = connection
        config = connection.config.get('docker', {})
        base_url = base_url or config.get('base_url')
        if base_url:
            cmd_args = ['-H {0}'.format(base_url)]
        else:
            cmd_args = []
        if tls or (tls is None and config.get('docker_tls')):
            cmd_args.append('--tls')
        self._out = DockerCommandLineOutput(cmd_prefix or config.get('cli_prefix'),
                                            default_bin or config.get('cli_bin', 'docker'), cmd_args or None)
        if use_sudo or (use_sudo is None and config.get('cli_sudo')):
            self._call_method = connection.sudo
        else:
            self._call_method = connection.run
        self._quiet = not (debug or (debug is None and config.get('cli_debug')))
        self.api_version = None
        self._update_api_version()

    def _call(self, cmd, quiet=False, **kwargs):
        if cmd:
            if quiet and self._quiet:
                hide = 'stdout'
            else:
                hide = None
            res = self._call_method(cmd, shell=False, hide=hide, **kwargs)
            return res.stdout
        return None

    def create_container(self, *args, **kwargs):
        cmd_str = self._out.get_cmd('create_container', *args, **kwargs)
        return {'Id': self._call(cmd_str)}

    def start(self, *args, **kwargs):
        cmd_str = self._out.get_cmd('start', *args, **kwargs)
        self._call(cmd_str)

    def restart(self, *args, **kwargs):
        cmd_str = self._out.get_cmd('restart', *args, **kwargs)
        self._call(cmd_str)

    def stop(self, *args, **kwargs):
        cmd_str = self._out.get_cmd('stop', *args, **kwargs)
        self._call(cmd_str)

    def remove_container(self, *args, **kwargs):
        cmd_str = self._out.get_cmd('remove_container', *args, **kwargs)
        self._call(cmd_str)

    def remove_image(self, *args, **kwargs):
        cmd_str = self._out.get_cmd('remove_image', *args, **kwargs)
        self._call(cmd_str)

    def kill(self, *args, **kwargs):
        cmd_str = self._out.get_cmd('kill', *args, **kwargs)
        self._call(cmd_str)

    def wait(self, *args, **kwargs):
        cmd_str = self._out.get_cmd('wait', *args, **kwargs)
        self._call(cmd_str)

    def containers(self, *args, **kwargs):
        cmd_str = self._out.get_cmd('containers', *args, **kwargs)
        res = self._call(cmd_str, quiet=True)
        return parse_containers_output(res)

    def inspect_container(self, *args, **kwargs):
        cmd_str = self._out.get_cmd('inspect_container', *args, **kwargs)
        res = self._call(cmd_str, quiet=True)
        return parse_inspect_output(res, 'container')

    def images(self, *args, **kwargs):
        cmd_str = self._out.get_cmd('images', *args, **kwargs)
        res = self._call(cmd_str, quiet=True)
        return parse_images_output(res)

    def pull(self, repository, tag=None, **kwargs):
        repo_tag = '{0}:{1}'.format(repository, tag) if tag else repository
        cmd_str = self._out.get_cmd('pull', repo_tag, **kwargs)
        self._call(cmd_str)

    def push(self, repository, tag=None, **kwargs):
        repo_tag = '{0}:{1}'.format(repository, tag) if tag else repository
        cmd_str = self._out.get_cmd('push', repo_tag, **kwargs)
        self._call(cmd_str)

    def create_network(self, *args, **kwargs):
        cmd_str = self._out.get_cmd('create_network', *args, **kwargs)
        return {'Id': self._call(cmd_str)}

    def remove_network(self, *args, **kwargs):
        cmd_str = self._out.get_cmd('remove_network', *args, **kwargs)
        self._call(cmd_str)

    def connect_container_to_network(self, *args, **kwargs):
        cmd_str = self._out.get_cmd('connect_container_to_network', *args, **kwargs)
        self._call(cmd_str)

    def disconnect_container_from_network(self, *args, **kwargs):
        cmd_str = self._out.get_cmd('disconnect_container_from_network', *args, **kwargs)
        self._call(cmd_str)

    def networks(self, *args, **kwargs):
        cmd_str = self._out.get_cmd('networks', *args, **kwargs)
        res = self._call(cmd_str, quiet=True)
        return parse_networks_output(res)

    def inspect_network(self, *args, **kwargs):
        cmd_str = self._out.get_cmd('inspect_network', *args, **kwargs)
        res = self._call(cmd_str, quiet=True)
        return parse_inspect_output(res, 'network')

    def create_volume(self, *args, **kwargs):
        cmd_str = self._out.get_cmd('create_volume', *args, **kwargs)
        return {'Name': self._call(cmd_str)}

    def remove_volume(self, *args, **kwargs):
        cmd_str = self._out.get_cmd('remove_volume', *args, **kwargs)
        self._call(cmd_str)

    def volumes(self, *args, **kwargs):
        cmd_str = self._out.get_cmd('volumes', *args, **kwargs)
        res = self._call(cmd_str, quiet=True)
        return {'Volumes': parse_volumes_output(res), 'Warnings': None}

    def inspect_volume(self, *args, **kwargs):
        cmd_str = self._out.get_cmd('inspect_volume', *args, **kwargs)
        res = self._call(cmd_str, quiet=True)
        return parse_inspect_output(res, 'volume')

    def exec_create(self, *args, **kwargs):
        cmd_str = self._out.get_cmd('exec_create', *args, **kwargs)
        self._call(cmd_str)

    def exec_start(self, *args, **kwargs):
        cmd_str = self._out.get_cmd('exec_start', *args, **kwargs)
        self._call(cmd_str)

    def top(self, container, ps_args):
        if ps_args:
            cmd_str = self._out.get_cmd('top', container, ps_args)
        else:
            cmd_str = self._out.get_cmd('top', container)
        res = self._call(cmd_str, quiet=True)
        return parse_top_output(res)

    def tag(self, image, repository, tag=None, **kwargs):
        if tag:
            repo_tag = '{0}:{1}'.format(repository, tag)
        else:
            repo_tag = repository
        cmd_str = self._out.get_cmd('tag', image, repo_tag, **kwargs)
        return self._call(cmd_str)

    def logs(self, *args, **kwargs):
        kwargs.pop('stream', None)
        cmd_str = self._out.get_cmd('logs', *args, **kwargs)
        return self._call(cmd_str, quiet=True)

    def login(self, **kwargs):
        config = self.connection.get('docker', {})
        set_registry_config_kwargs(kwargs, config)
        registry = kwargs.pop('registry')
        if registry:
            cmd_str = self._out.get_cmd('login', registry, **kwargs)
        else:
            cmd_str = self._out.get_cmd('login', **kwargs)
        res = self._call(cmd_str, quiet=True)
        lines = res.splitlines()
        print(lines)
        return 'Login Succeeded' in lines

    def build(self, tag, add_latest_tag=False, add_tags=None, raise_on_error=True, **kwargs):
        try:
            context = kwargs.pop('fileobj')
        except KeyError:
            raise ValueError("'fileobj' needs to be provided. Using 'path' is currently not implemented.")
        for a in ['custom_context', 'encoding']:
            kwargs.pop(a, None)

        c = self.connection
        with temp_dir(c) as remote_tmp:
            remote_fn = posixpath.join(remote_tmp, 'context')
            c.put(context, remote_fn)
            cmd_str = self._out.get_cmd('build', '- <', remote_fn, tag=tag, **kwargs)
            res = self._call(cmd_str, warn=not raise_on_error)
        if res:
            image_id = _find_image_id(res)
            if image_id:
                self.add_extra_tags(image_id, tag, add_tags, add_latest_tag)
                return image_id
        return None

    def version(self, **kwargs):
        kwargs.pop('api_version', None)
        cmd_str = self._out.get_cmd('version')
        res = self._call(cmd_str, quiet=True)
        version_dict = parse_version_output(res)
        return version_dict

    def info(self):
        cmd_str = self._out.get_cmd('info')
        res = self._call(cmd_str, quiet=True)
        info_dict = parse_info_output(res)
        return info_dict

    def push_log(self, info, level, *args, **kwargs):
        pass

    def _update_api_version(self):
        if self.api_version and self.api_version != 'auto':
            return
        version_dict = self.version()
        if 'APIVersion' in version_dict:
            self.api_version = version_dict['APIVersion']
        elif 'ApiVersion' in version_dict:
            self.api_version = version_dict['ApiVersion']

    def run_cmd(self, command):
        self.connection.sudo(command)


class DockerCliConfig(ClientConfiguration):
    init_kwargs = 'connection', 'base_url', 'tls', 'cmd_prefix', 'default_bin', 'use_sudo', 'debug'
    client_constructor = DockerCliClient

    def update_settings(self, **kwargs):
        super(DockerCliConfig, self).update_settings(**kwargs)
        self._features['host_config'] = USE_HC_MERGE


class ContainerCliFabricClient(FabricContainerClient):
    configuration_class = DockerCliConfig


def copy_resource(c, container, resource, local_filename, contents_only=True):
    """
    Copies a resource from a container to a compressed tarball and downloads it.

    :param c: Fabric connection.
    :type c: fabric.connection.Connection
    :param container: Container name or id.
    :type container: unicode | str
    :param resource: Name of resource to copy.
    :type resource: unicode | str
    :param local_filename: Path to store the tarball locally.
    :type local_filename: unicode | str
    :param contents_only: In case ``resource`` is a directory, put all contents at the root of the tar file. If this is
      set to ``False``, the directory itself will be at the root instead.
    :type contents_only: bool
    """
    with temp_dir(c) as remote_tmp:
        base_name = os.path.basename(resource)
        copy_path = posixpath.join(remote_tmp, 'copy_tmp')
        c.run(mkdir(copy_path, check_if_exists=True))
        remote_name = posixpath.join(copy_path, base_name)
        archive_name = 'container_{0}.tar.gz'.format(container)
        archive_path = posixpath.join(remote_tmp, archive_name)
        c.run('docker cp {0}:{1} {2}'.format(container, resource, copy_path), shell=False)
        if contents_only and is_directory(c, remote_name):
            src_dir = remote_name
            src_files = '*'
        else:
            src_dir = copy_path
            src_files = base_name
        with c.cd(src_dir):
            c.run(targz(archive_path, src_files))
        c.get(archive_path, local_filename)


def copy_resources(c, src_container, src_resources, storage_dir, dst_directories=None, apply_chown=None,
                   apply_chmod=None):
    """
    Copies files and directories from a Docker container. Multiple resources can be copied and additional options are
    available than in :func:`copy_resource`. Unlike in :func:`copy_resource`, Resources are copied as they are and not
    compressed to a tarball, and they are left on the remote machine.

    :param c: Fabric connection.
    :type c: fabric.connection.Connection
    :param src_container: Container name or id.
    :type src_container: unicode | str
    :param src_resources: Resources, as (file or directory) names to copy.
    :type src_resources: collections.Iterable[unicode | str]
    :param storage_dir: Remote directory to store the copied objects in.
    :type storage_dir: unicode | str
    :param dst_directories: Optional dictionary of destination directories, in the format ``resource: destination``. If
      not set, resources will be in the same relative structure to one another as inside the container. For setting a
      common default, use ``*`` as the resource key.
    :type dst_directories: dict[unicode | str, unicode | str]
    :param apply_chown: Owner to set for the copied resources. Can be a user name or id, group name or id, both in the
      notation ``user:group``, or as a tuple ``(user, group)``.
    :type apply_chown: unicode | str | tuple
    :param apply_chmod: File system permissions to set for the copied resources. Can be any notation as accepted by
      `chmod`.
    :type apply_chmod: unicode | str
    """
    def _copy_resource(resource):
        default_dest_path = generic_path if generic_path is not None else resource
        dest_path = directories.get(resource, default_dest_path).strip(posixpath.sep)
        head, tail = posixpath.split(dest_path)
        rel_path = posixpath.join(storage_dir, head)
        c.run(mkdir(rel_path, check_if_exists=True))
        c.run('docker cp {0}:{1} {2}'.format(src_container, resource, rel_path), shell=False)

    directories = dst_directories or {}
    generic_path = directories.get('*')
    for res in src_resources:
        _copy_resource(res)
    if apply_chmod:
        c.run(chmod(apply_chmod, storage_dir))
    if apply_chown:
        c.sudo(chown(apply_chown, storage_dir))


def isolate_and_get(c, src_container, src_resources, local_dst_dir, **kwargs):
    """
    Uses :func:`copy_resources` to copy resources from a container, but afterwards generates a compressed tarball
    and downloads it.

    :param c: Fabric connection.
    :type c: fabric.connection.Connection
    :param src_container: Container name or id.
    :type src_container: unicode | str
    :param src_resources: Resources, as (file or directory) names to copy.
    :type src_resources: collections.Iterable[unicode | str]
    :param local_dst_dir: Local directory to store the compressed tarball in. Can also be a file name; the default file
      name is ``container_<container name>.tar.gz``.
    :type local_dst_dir: unicode | str
    :param kwargs: Additional kwargs for :func:`copy_resources`.
    """
    with temp_dir(c) as remote_tmp:
        copy_path = posixpath.join(remote_tmp, 'copy_tmp')
        archive_path = posixpath.join(remote_tmp, 'container_{0}.tar.gz'.format(src_container))
        copy_resources(c, src_container, src_resources, copy_path, **kwargs)
        with c.cd(copy_path):
            c.sudo(targz(archive_path, '*'))
        c.get(archive_path, local_dst_dir)


def isolate_to_image(c, src_container, src_resources, dst_image, **kwargs):
    """
    Uses :func:`copy_resources` to copy resources from a container, but afterwards imports the contents into a new
    (otherwise empty) Docker image.

    :param c: Fabric connection.
    :type c: fabric.connection.Connection
    :param src_container: Container name or id.
    :type src_container: unicode | str
    :param src_resources: Resources, as (file or directory) names to copy.
    :type src_resources: collections.Iterable[unicode | str]
    :param dst_image: Tag for the new image.
    :type dst_image: unicode | str
    :param kwargs: Additional kwargs for :func:`copy_resources`.
    """
    with temp_dir(c) as remote_tmp:
        copy_resources(c, src_container, src_resources, remote_tmp, **kwargs)
        with c.cd(remote_tmp):
            c.sudo('tar -cz * | docker import - {0}'.format(dst_image))


def save_image(c, image, local_filename):
    """
    Saves a Docker image as a compressed tarball. This command line client method is a suitable alternative, if the
    Remove API method is too slow.

    :param c: Fabric connection.
    :type c: fabric.connection.Connection
    :param image: Image id or tag.
    :type image: unicode | str
    :param local_filename: Local file name to store the image into. If this is a directory, the image will be stored
      there as a file named ``image_<Image name>.tar.gz``.
    """
    r_name, __, i_name = image.rpartition('/')
    i_name = i_name.partition(':')[0]
    with temp_dir(c) as remote_tmp:
        archive = posixpath.join(remote_tmp, 'image_{0}.tar.gz'.format(i_name))
        c.run('docker save {0} | gzip --stdout > {1}'.format(image, archive), shell=False)
        c.get(archive, local_filename)


def flatten_image(c, image, dest_image=None, **kwargs):
    """
    Exports a Docker image's file system and re-imports it into a new (otherwise new) image. Note that this does not
    transfer the image configuration. In order to gain access to the container contents, the image is started with a
    non-operational command, such as ``/bin/true``. The container is removed once the new image has been created.

    :param c: Fabric connection.
    :type c: fabric.connection.Connection
    :param image: Image id or tag.
    :type image: unicode | str
    :param dest_image: Tag for the new image.
    :type dest_image: unicode | str
    :param kwargs: Additional kwargs for the temporary container.
    """
    dest_image = dest_image or image
    with temp_container(c, image, **kwargs) as tc:
        c.run('docker export {0} | docker import - {1}'.format(tc, dest_image), shell=False)
