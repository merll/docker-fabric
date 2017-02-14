# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os
import posixpath

from fabric.api import cd, env, fastprint, get, put, run, settings, sudo
from fabric.network import needs_host

from dockermap.api import USE_HC_MERGE
from dockermap.client.cli import (DockerCommandLineOutput, parse_containers_output, parse_inspect_output,
                                  parse_images_output, parse_version_output, parse_top_output)
from dockermap.client.docker_util import DockerUtilityMixin
from dockermap.shortcuts import chmod, chown, targz, mkdir

from .base import DockerConnectionDict, FabricContainerClient, FabricClientConfiguration
from .utils.containers import temp_container
from .utils.files import temp_dir, is_directory


class DockerCliClient(DockerUtilityMixin):
    """
    Docker client for Fabric using the command line interface on a remote host.

    :param cmd_prefix: Custom prefix to prepend to the Docker command line.
    :type cmd_prefix: unicode
    :param default_bin: Docker binary to use. If not set, uses ``docker``.
    :type default_bin: unicode
    :param base_url: URL to connect to; if not set, will refer to ``env.docker_base_url`` or use ``None``, which by
     default attempts a connection on a Unix socket at ``/var/run/docker.sock``.
    :type base_url: unicode
    :param tls: Whether to use TLS on the connection to the Docker service.
    :type tls: bool
    :param use_sudo: Whether to use ``sudo`` when performing Docker commands.
    :type use_sudo: bool
    :param debug: If set to ``True``, echoes each command and its console output. Some commands are echoed either way
     for some feedback.
    :type debug: bool
    """
    def __init__(self, cmd_prefix=None, default_bin=None, base_url=None, tls=None, use_sudo=None, debug=None):
        super(DockerCliClient, self).__init__()
        base_url = base_url or env.get('docker_base_url')
        if base_url:
            cmd_args = ['-H {0}'.format(base_url)]
        else:
            cmd_args = []
        if tls or (tls is None and env.get('docker_tls')):
            cmd_args.append('--tls')
        self._out = DockerCommandLineOutput(cmd_prefix or env.get('docker_cli_prefix'),
                                            default_bin or env.get('docker_cli_bin', 'docker'), cmd_args or None)
        if use_sudo or (use_sudo is None and env.get('docker_cli_sudo')):
            self._call_method = sudo
        else:
            self._call_method = run
        self._quiet = not (debug or (debug is None and env.get('docker_cli_debug')))
        self.api_version = None
        self._update_api_version()

    def _call(self, cmd, quiet=False):
        if cmd:
            return self._call_method(cmd, shell=False, quiet=quiet and self._quiet)
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
        return parse_inspect_output(res)

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
        for key, variable in [
            ('username', 'user'),
            ('password', 'password'),
            ('email', 'mail'),
            ('registry', 'repository'),
            ('insecure_registry', 'insecure')
        ]:
            if key not in kwargs:
                env_value = env.get('docker_registry_{0}'.format(variable))
                if env_value:
                    kwargs[key] = env_value
        registry = kwargs.pop('registry', env.get('docker_registry_repository'))
        if registry:
            cmd_str = self._out.get_cmd('login', registry, **kwargs)
        else:
            cmd_str = self._out.get_cmd('login', **kwargs)
        res = self._call(cmd_str, quiet=True)
        lines = res.splitlines()
        fastprint(lines)
        return 'Login Succeeded' in lines

    def build(self, tag, add_latest_tag=False, add_tags=None, raise_on_error=False, **kwargs):
        try:
            context = kwargs.pop('fileobj')
        except KeyError:
            raise ValueError("'fileobj' needs to be provided. Using 'path' is currently not implemented.")
        for a in ['custom_context', 'encoding']:
            kwargs.pop(a, None)

        with temp_dir() as remote_tmp:
            remote_fn = posixpath.join(remote_tmp, 'context')
            put(context, remote_fn)
            cmd_str = self._out.get_cmd('build', '- <', remote_fn, tag=tag, **kwargs)
            with settings(warn_only=not raise_on_error):
                res = self._call(cmd_str)
        if res:
            last_log = res.splitlines()[-1]
            if last_log and last_log.startswith('Successfully built '):
                image_id = last_log[19:]  # Remove prefix
                self.add_extra_tags(image_id, tag, add_tags, add_latest_tag)
                return image_id
        return None

    def version(self, **kwargs):
        kwargs.pop('api_version', None)
        cmd_str = self._out.get_cmd('version')
        res = self._call(cmd_str, quiet=True)
        version_dict = parse_version_output(res)
        return version_dict

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


class DockerCliConfig(FabricClientConfiguration):
    init_kwargs = 'base_url', 'tls', 'cmd_prefix', 'default_bin', 'use_sudo', 'debug'
    client_constructor = DockerCliClient

    def update_settings(self, **kwargs):
        super(DockerCliConfig, self).update_settings(**kwargs)
        self.use_host_config = USE_HC_MERGE


class DockerCliConnections(DockerConnectionDict):
    configuration_class = DockerCliConfig


class ContainerCliFabricClient(FabricContainerClient):
    configuration_class = DockerCliConfig


docker_cli = DockerCliConnections().get_connection
container_cli = ContainerCliFabricClient


@needs_host
def copy_resource(container, resource, local_filename, contents_only=True):
    """
    Copies a resource from a container to a compressed tarball and downloads it.

    :param container: Container name or id.
    :type container: unicode
    :param resource: Name of resource to copy.
    :type resource: unicode
    :param local_filename: Path to store the tarball locally.
    :type local_filename: unicode
    :param contents_only: In case ``resource`` is a directory, put all contents at the root of the tar file. If this is
      set to ``False``, the directory itself will be at the root instead.
    :type contents_only: bool
    """
    with temp_dir() as remote_tmp:
        base_name = os.path.basename(resource)
        copy_path = posixpath.join(remote_tmp, 'copy_tmp')
        run(mkdir(copy_path, check_if_exists=True))
        remote_name = posixpath.join(copy_path, base_name)
        archive_name = 'container_{0}.tar.gz'.format(container)
        archive_path = posixpath.join(remote_tmp, archive_name)
        run('docker cp {0}:{1} {2}'.format(container, resource, copy_path), shell=False)
        if contents_only and is_directory(remote_name):
            src_dir = remote_name
            src_files = '*'
        else:
            src_dir = copy_path
            src_files = base_name
        with cd(src_dir):
            run(targz(archive_path, src_files))
        get(archive_path, local_filename)


@needs_host
def copy_resources(src_container, src_resources, storage_dir, dst_directories=None, apply_chown=None, apply_chmod=None):
    """
    Copies files and directories from a Docker container. Multiple resources can be copied and additional options are
    available than in :func:`copy_resource`. Unlike in :func:`copy_resource`, Resources are copied as they are and not
    compressed to a tarball, and they are left on the remote machine.

    :param src_container: Container name or id.
    :type src_container: unicode
    :param src_resources: Resources, as (file or directory) names to copy.
    :type src_resources: iterable
    :param storage_dir: Remote directory to store the copied objects in.
    :type storage_dir: unicode
    :param dst_directories: Optional dictionary of destination directories, in the format ``resource: destination``. If
      not set, resources will be in the same relative structure to one another as inside the container. For setting a
      common default, use ``*`` as the resource key.
    :type dst_directories: dict
    :param apply_chown: Owner to set for the copied resources. Can be a user name or id, group name or id, both in the
      notation ``user:group``, or as a tuple ``(user, group)``.
    :type apply_chown: unicode or tuple
    :param apply_chmod: File system permissions to set for the copied resources. Can be any notation as accepted by
      `chmod`.
    :type apply_chmod: unicode
    """
    def _copy_resource(resource):
        default_dest_path = generic_path if generic_path is not None else resource
        dest_path = directories.get(resource, default_dest_path).strip(posixpath.sep)
        head, tail = posixpath.split(dest_path)
        rel_path = posixpath.join(storage_dir, head)
        run(mkdir(rel_path, check_if_exists=True))
        run('docker cp {0}:{1} {2}'.format(src_container, resource, rel_path), shell=False)

    directories = dst_directories or {}
    generic_path = directories.get('*')
    for res in src_resources:
        _copy_resource(res)
    if apply_chmod:
        run(chmod(apply_chmod, storage_dir))
    if apply_chown:
        sudo(chown(apply_chown, storage_dir))


@needs_host
def isolate_and_get(src_container, src_resources, local_dst_dir, **kwargs):
    """
    Uses :func:`copy_resources` to copy resources from a container, but afterwards generates a compressed tarball
    and downloads it.

    :param src_container: Container name or id.
    :type src_container: unicode
    :param src_resources: Resources, as (file or directory) names to copy.
    :type src_resources: iterable
    :param local_dst_dir: Local directory to store the compressed tarball in. Can also be a file name; the default file
      name is ``container_<container name>.tar.gz``.
    :type local_dst_dir: unicode
    :param kwargs: Additional kwargs for :func:`copy_resources`.
    """
    with temp_dir() as remote_tmp:
        copy_path = posixpath.join(remote_tmp, 'copy_tmp')
        archive_path = posixpath.join(remote_tmp, 'container_{0}.tar.gz'.format(src_container))
        copy_resources(src_container, src_resources, copy_path, **kwargs)
        with cd(copy_path):
            sudo(targz(archive_path, '*'))
        get(archive_path, local_dst_dir)


@needs_host
def isolate_to_image(src_container, src_resources, dst_image, **kwargs):
    """
    Uses :func:`copy_resources` to copy resources from a container, but afterwards imports the contents into a new
    (otherwise empty) Docker image.

    :param src_container: Container name or id.
    :type src_container: unicode
    :param src_resources: Resources, as (file or directory) names to copy.
    :type src_resources: iterable
    :param dst_image: Tag for the new image.
    :type dst_image: unicode
    :param kwargs: Additional kwargs for :func:`copy_resources`.
    """
    with temp_dir() as remote_tmp:
        copy_resources(src_container, src_resources, remote_tmp, **kwargs)
        with cd(remote_tmp):
            sudo('tar -cz * | docker import - {0}'.format(dst_image))


@needs_host
def save_image(image, local_filename):
    """
    Saves a Docker image as a compressed tarball. This command line client method is a suitable alternative, if the
    Remove API method is too slow.

    :param image: Image id or tag.
    :type image: unicode
    :param local_filename: Local file name to store the image into. If this is a directory, the image will be stored
      there as a file named ``image_<Image name>.tar.gz``.
    """
    r_name, __, i_name = image.rpartition('/')
    i_name, __, __ = i_name.partition(':')
    with temp_dir() as remote_tmp:
        archive = posixpath.join(remote_tmp, 'image_{0}.tar.gz'.format(i_name))
        run('docker save {0} | gzip --stdout > {1}'.format(image, archive), shell=False)
        get(archive, local_filename)


@needs_host
def flatten_image(image, dest_image=None, no_op_cmd='/bin/true', create_kwargs={}, start_kwargs={}):
    """
    Exports a Docker image's file system and re-imports it into a new (otherwise new) image. Note that this does not
    transfer the image configuration. In order to gain access to the container contents, the image is started with a
    non-operational command, such as ``/bin/true``. The container is removed once the new image has been created.

    :param image: Image id or tag.
    :type image: unicode
    :param dest_image: Tag for the new image.
    :type dest_image: unicode
    :param no_op_cmd: Dummy command for starting temporary container.
    :type no_op_cmd: unicode
    :param create_kwargs: Optional additional kwargs for creating the temporary container.
    :type create_kwargs: dict
    :param start_kwargs: Optional additional kwargs for starting the temporary container.
    :type start_kwargs: dict
    """
    dest_image = dest_image or image
    with temp_container(image, no_op_cmd=no_op_cmd, create_kwargs=create_kwargs, start_kwargs=start_kwargs) as c:
        run('docker export {0} | docker import - {1}'.format(c, dest_image), shell=False)
