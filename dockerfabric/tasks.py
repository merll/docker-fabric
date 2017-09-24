# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from datetime import datetime
import itertools
from fabric.api import env, run, runs_once, sudo, task
from fabric.utils import puts, fastprint
import six

from dockermap.utils import expand_path
from . import cli
from .api import docker_fabric
from .utils.net import get_ip4_address, get_ip6_address
from .utils.output import stdout_result


IMAGE_COLUMNS = ('Id', 'RepoTags', 'ParentId', 'Created', 'VirtualSize', 'Size')
CONTAINER_COLUMNS = ('Id', 'Names', 'Image', 'Command', 'Ports', 'Status', 'Created')
NETWORK_COLUMNS = ('Id', 'Name', 'Driver', 'Scope')
VOLUME_COLUMNS = ('Name', 'Driver')


def _format_output_table(data_dict, columns, full_ids=False, full_cmd=False, short_image=False):
    def _format_port(port_dict):
        if 'PublicPort' in port_dict and 'IP' in port_dict:
            return '{IP}:{PublicPort}->{PrivatePort}/{Type}'.format(**port_dict)
        return '{PrivatePort}/{Type}'.format(**port_dict)

    def _get_column(item, column):
        data = item.get(column, '')
        if isinstance(data, list):
            if column == 'Ports':
                return map(_format_port, data)
            return data
        if column in ('Id', 'ParentId') and not full_ids:
            return data[:12],
        if column == 'Created':
            return datetime.utcfromtimestamp(data).isoformat(),
        if column == 'Command' and not full_cmd:
            return data[:25],
        if column == 'Image' and short_image:
            __, __, i_name = data.rpartition('/')
            return i_name,
        return unicode(data),

    def _max_len(col_data):
        if col_data:
            return max(map(len, col_data))
        return 0

    puts('')
    rows = [[[c] for c in columns]]
    rows.extend([_get_column(i, col) for col in columns] for i in data_dict)
    col_lens = map(max, (map(_max_len, c) for c in zip(*rows)))
    row_format = '  '.join('{{{0}:{1}}}'.format(i, l) for i, l in enumerate(col_lens))
    for row in rows:
        for c in itertools.izip_longest(*row, fillvalue=''):
            fastprint(row_format.format(*c), end='\n', flush=False)
    fastprint('', flush=True)


@task
def reset_socat(use_sudo=False):
    """
    Finds and closes all processes of `socat`.

    :param use_sudo: Use `sudo` command. As Docker-Fabric does not run `socat` with `sudo`, this is by default set to
      ``False``. Setting it to ``True`` could unintentionally remove instances from other users.
    :type use_sudo: bool
    """
    output = stdout_result('ps -o pid -C socat', quiet=True)
    pids = output.split('\n')[1:]
    puts("Removing process(es) with id(s) {0}.".format(', '.join(pids)))
    which = sudo if use_sudo else run
    which('kill {0}'.format(' '.join(pids)), quiet=True)


@task
def version():
    """
    Shows version information of the remote Docker service, similar to ``docker version``.
    """
    output = docker_fabric().version()
    col_len = max(map(len, output.keys())) + 1
    puts('')
    for k, v in six.iteritems(output):
        fastprint('{0:{1}} {2}'.format(''.join((k, ':')), col_len, v), end='\n', flush=False)
    fastprint('', flush=True)


@task
def get_ip(interface_name='docker0'):
    """
    Shows the IP4 address of a network interface.

    :param interface_name: Name of the network interface. Default is ``docker0``.
    :type interface_name: unicode
    """
    puts(get_ip4_address(interface_name))


@task
def get_ipv6(interface_name='docker0', expand=False):
    """
    Shows the IP6 address of a network interface.

    :param interface_name: Name of the network interface. Default is ``docker0``.
    :type interface_name: unicode
    :param expand: Expand the abbreviated IP6 address. Default is ``False``.
    :type expand: bool
    """
    puts(get_ip6_address(interface_name, expand=expand))


@task
def list_images(list_all=False, full_ids=False):
    """
    Lists images on the Docker remote host, similar to ``docker images``.

    :param list_all: Lists all images (e.g. dependencies). Default is ``False``, only shows named images.
    :type list_all: bool
    :param full_ids: Shows the full ids. When ``False`` (default) only shows the first 12 characters.
    :type full_ids: bool
    """
    images = docker_fabric().images(all=list_all)
    _format_output_table(images, IMAGE_COLUMNS, full_ids)


@task
def list_containers(list_all=True, short_image=True, full_ids=False, full_cmd=False):
    """
    Lists containers on the Docker remote host, similar to ``docker ps``.

    :param list_all: Shows all containers. Default is ``False``, which omits exited containers.
    :type list_all: bool
    :param short_image: Hides the repository prefix for preserving space. Default is ``True``.
    :type short_image: bool
    :param full_ids: Shows the full image ids. When ``False`` (default) only shows the first 12 characters.
    :type full_ids: bool
    :param full_cmd: Shows the full container command. When ``False`` (default) only shows the first 25 characters.
    :type full_cmd: bool
    """
    containers = docker_fabric().containers(all=list_all)
    _format_output_table(containers, CONTAINER_COLUMNS, full_ids, full_cmd, short_image)


@task
def list_networks(full_ids=False):
    """
    Lists networks on the Docker remote host, similar to ``docker network ls``.

    :param full_ids: Shows the full network ids. When ``False`` (default) only shows the first 12 characters.
    :type full_ids: bool
    """
    networks = docker_fabric().networks()
    _format_output_table(networks, NETWORK_COLUMNS, full_ids)


@task
def list_volumes():
    """
    Lists volumes on the Docker remote host, similar to ``docker volume ls``.
    """
    volumes = docker_fabric().volumes()['Volumes'] or ()
    _format_output_table(volumes, VOLUME_COLUMNS)


@task
def cleanup_containers(**kwargs):
    """
    Removes all containers that have finished running. Similar to the ``prune`` functionality in newer Docker versions.
    """
    containers = docker_fabric().cleanup_containers(**kwargs)
    if kwargs.get('list_only'):
        puts('Existing containers:')
        for c_id, c_name in containers:
            fastprint('{0}  {1}'.format(c_id, c_name), end='\n')


@task
def cleanup_images(remove_old=False, **kwargs):
    """
    Removes all images that have no name, and that are not references as dependency by any other named image. Similar
    to the ``prune`` functionality in newer Docker versions, but supports more filters.

    :param remove_old: Also remove images that do have a name, but no `latest` tag.
    :type remove_old: bool
    """
    keep_tags = env.get('docker_keep_tags')
    if keep_tags is not None:
        kwargs.setdefault('keep_tags', keep_tags)
    removed_images = docker_fabric().cleanup_images(remove_old=remove_old, **kwargs)
    if kwargs.get('list_only'):
        puts('Unused images:')
        for image_name in removed_images:
            fastprint(image_name, end='\n')


@task
def remove_all_containers(**kwargs):
    """
    Stops and removes all containers from the remote. Use with caution outside of a development environment!
    :return:
    """
    containers = docker_fabric().remove_all_containers(**kwargs)
    if kwargs.get('list_only'):
        puts('Existing containers:')
        for c_id in containers[1]:
            fastprint(c_id, end='\n')


@task
@runs_once
def save_image(image, filename=None):
    """
    Saves a Docker image from the remote to a local files. For performance reasons, uses the Docker command line client
    on the host, generates a gzip-tarball and downloads that.

    :param image: Image name or id.
    :type image: unicode
    :param filename: File name to store the local file. If not provided, will use ``<image>.tar.gz`` in the current
      working directory.
    :type filename: unicode
    """
    local_name = filename or '{0}.tar.gz'.format(image)
    cli.save_image(image, local_name)


@task
def load_image(filename, timeout=120):
    """
    Uploads an image from a local file to a Docker remote. Note that this temporarily has to extend the service timeout
    period.

    :param filename: Local file name.
    :type filename: unicode
    :param timeout: Timeout in seconds to set temporarily for the upload.
    :type timeout: int
    """
    c = docker_fabric()
    with open(expand_path(filename), 'r') as f:
        _timeout = c._timeout
        c._timeout = timeout
        try:
            c.load_image(f)
        finally:
            c._timeout = _timeout
