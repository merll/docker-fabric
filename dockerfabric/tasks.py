# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from datetime import datetime
from fabric import task
import six
from six.moves import map, zip, zip_longest

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
            return data.rpartition('/')[2],
        return six.text_type(data),

    def _max_len(col_data):
        cd_tuple = tuple(col_data)
        if cd_tuple:
            return max(map(len, cd_tuple))
        return 0

    print('')
    rows = [[[c] for c in columns]]
    rows.extend([_get_column(i, col) for col in columns] for i in data_dict)
    col_lens = map(max, (map(_max_len, c) for c in zip(*rows)))
    row_format = '  '.join('{{{0}:{1}}}'.format(i, l) for i, l in enumerate(col_lens))
    for row in rows:
        for c in zip_longest(*row, fillvalue=''):
            print(row_format.format(*c), end='\n', flush=False)
    print('', flush=True)


def _format_info(output):
    col_len = max(map(len, output.keys())) + 1
    print('')
    for k, v in six.iteritems(output):
        print('{0:{1}} {2}'.format(''.join((k, ':')), col_len, v), end='\n', flush=False)
    print('', flush=True)


@task(help={
    'use_sudo': "Use 'sudo' command. As Docker-Fabric does not run 'socat' with 'sudo', this is by default not set. "
                "It could unintentionally remove instances from other users."
})
def reset_socat(c, use_sudo=False):
    """
    Finds and closes all processes of `socat`.
    """
    output = stdout_result(c, 'ps -o pid -C socat', quiet=True)
    pids = output.split('\n')[1:]
    print("Removing process(es) with id(s) {0}.".format(', '.join(pids)))
    which = c.sudo if use_sudo else c.run
    which('kill {0}'.format(' '.join(pids)), quiet=True)


@task
def version(c):
    """
    Shows version information of the remote Docker service, similar to 'docker version'.
    """
    output = docker_fabric(c).version()
    _format_info(output)


@task
def info(c):
    """
    Shows configuration and environment information of the remote Docker service, similar to 'docker info'.
    """
    output = docker_fabric(c).info()
    _format_info(output)


@task(help={
    'interface_name': "Name of the network interface. Default is 'docker0'."
})
def get_ip(c, interface_name='docker0'):
    """
    Shows the IP4 address of a network interface.
    """
    print(get_ip4_address(c, interface_name))


@task(help={
    'interface_name': "Name of the network interface. Default is 'docker0'.",
    'expand': "Expand the abbreviated IP6 address."
})
def get_ipv6(c, interface_name='docker0', expand=False):
    """
    Shows the IP6 address of a network interface.
    """
    print(get_ip6_address(c, interface_name, expand=expand))


@task(help={
    'list_all': "Lists all images (e.g. dependencies). By default only shows named images.",
    'full_ids': "Shows the full ids. By default only shows the first 12 characters."
})
def list_images(c, list_all=False, full_ids=False):
    """
    Lists images on the Docker remote host, similar to ``docker images``.
    """
    images = docker_fabric(c).images(all=list_all)
    _format_output_table(images, IMAGE_COLUMNS, full_ids)


@task(help={
    'list_all': "Shows all containers. By default omits exited containers.",
    'long_image': "Shows the repository prefix, hidden by default for preserving space.",
    'full_ids': "Shows the full ids. By default only shows the first 12 characters.",
    'full_cmd': "Shows the full container command. By default only shows the first 25 characters."
})
def list_containers(c, list_all=False, long_image=False, full_ids=False, full_cmd=False):
    """
    Lists containers on the Docker remote host, similar to ``docker ps``.
    """
    containers = docker_fabric(c).containers(all=list_all)
    _format_output_table(containers, CONTAINER_COLUMNS, full_ids, full_cmd, not long_image)


@task(help={
    'full_ids': "Shows the full network ids. By default only shows the first 12 characters.",
})
def list_networks(c, full_ids=False):
    """
    Lists networks on the Docker remote host, similar to ``docker network ls``.
    """
    networks = docker_fabric(c).networks()
    _format_output_table(networks, NETWORK_COLUMNS, full_ids)


@task
def list_volumes(c):
    """
    Lists volumes on the Docker remote host, similar to ``docker volume ls``.
    """
    volumes = docker_fabric(c).volumes()['Volumes'] or ()
    _format_output_table(volumes, VOLUME_COLUMNS)


@task(help={
    'include_initial': "Consider containers that have never been started.",
    'exclude': "Comma-separated container names to exclude from the cleanup process.",
    'list_only': "Only lists containers, but does not actually remove them."
})
def cleanup_containers(c, include_initial=False, exclude=None, list_only=False):
    """
    Removes all containers that have finished running. Similar to the ``prune`` functionality in newer Docker versions.
    """
    if exclude and isinstance(exclude, str):
        exclude = exclude.split(',')
    containers = docker_fabric(c).cleanup_containers(include_initial=include_initial, exclude=exclude,
                                                     list_only=list_only)
    if list_only:
        print('Existing containers:')
        for c_id, c_name in containers:
            print('{0}  {1}'.format(c_id, c_name), end='\n')


@task(help={
    'remove_old': "Also removes images that have repository names, but no 'latest' tag.",
    'keep_tags': "Comma-separated enumeration of tags to not remove.",
    'force': "If an image is referenced by multiple repositories, Docker by default will not remove the image. "
             "This setting forces the removal.",
    'list_only': "Only lists images, but does not actually remove them."
})
def cleanup_images(c, remove_old=False, keep_tags=None, force=False, list_only=False):
    """
    Removes all images that have no name, and that are not references as dependency by any other named image. Similar
    to the ``prune`` functionality in newer Docker versions, but supports more filters.
    """
    kwargs = dict(remove_old=remove_old, force=force, list_only=list_only)
    config = c.config.get('docker', {})
    keep_tags = keep_tags or config.get('keep_tags')
    if keep_tags:
        if isinstance(keep_tags, str):
            keep_tags = keep_tags.split(',')
        kwargs.setdefault('keep_tags', keep_tags)
    removed_images = docker_fabric(c).cleanup_images(**kwargs)
    if list_only:
        print('Unused images:')
        for image_name in removed_images:
            print(image_name, end='\n')


@task(help={
    'stop_timeout': "Timeout to stopping each container.",
    'list_only': "When set, only lists containers, but does not actually stop or remove them."
})
def remove_all_containers(c, stop_timeout=10, list_only=False):
    """
    Stops and removes all containers from the remote. Use with caution outside of a development environment!
    """
    containers = docker_fabric(c).remove_all_containers(stop_timeout=stop_timeout, list_only=list_only)
    if list_only:
        print('Existing containers:')
        for c_id in containers[1]:
            print(c_id, end='\n')


@task(help={
    'image': "Image name or id.",
    'filename': "File name to store the local file. If not provided, will use '<image>.tar.gz' in the current "
                "working directory."
})
# FIXME: reactivate when available: @runs_once
def save_image(c, image, filename=None):
    """
    Saves a Docker image from the remote to a local files. For performance reasons, uses the Docker command line client
    on the host, generates a gzip-tarball and downloads that.
    """
    local_name = filename or '{0}.tar.gz'.format(image)
    cli.save_image(c, image, local_name)


@task(help={
    'filename': "Local file name.",
    'timeout': "Timeout in seconds to set temporarily for the upload."
})
def load_image(c, filename, timeout=120):
    """
    Uploads an image from a local file to a Docker remote. Note that this temporarily has to extend the service timeout
    period.
    """
    df = docker_fabric(c)
    with open(expand_path(filename), 'r') as f:
        _timeout = df._timeout
        df._timeout = timeout
        try:
            df.load_image(f)
        finally:
            df._timeout = _timeout
