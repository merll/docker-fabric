# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from datetime import datetime
import itertools
import os
from fabric.api import cd, env, get, put, run, runs_once, sudo, task
from fabric.utils import error, puts, fastprint
import six

from dockermap.shortcuts import curl, untargz
from dockermap.utils import expand_path
from . import DEFAULT_SOCAT_VERSION, cli
from .api import docker_fabric
from .utils.files import temp_dir
from .utils.net import get_ip4_address, get_ip6_address
from .utils.output import stdout_result
from .utils.users import assign_user_groups


SOCAT_URL = 'http://www.dest-unreach.org/socat/download/socat-{0}.tar.gz'
IMAGE_COLUMNS = ('Id', 'RepoTags', 'ParentId', 'Created', 'VirtualSize', 'Size')
CONTAINER_COLUMNS = ('Id', 'Names', 'Image', 'Command', 'Ports', 'Status', 'Created')


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
def install_docker_ubuntu(skip_group_assignment=False):
    """
    Installs Docker on a remote machine running Ubuntu and adds the current user to the ``docker`` user group.

    :param skip_group_assignment: If set to ``True``, skips the assignment to the ``docker`` group.
    :type skip_group_assignment: bool
    """
    sudo('apt-key adv --keyserver hkp://p80.pool.sks-keyservers.net:80 '
         '--recv-keys 58118E89F3A912897C070ADBF76221572C52609D')
    sudo('echo deb https://apt.dockerproject.org/repo ubuntu-`lsb_release -c -s` main > '
         '/etc/apt/sources.list.d/docker.list')
    sudo('apt-get update -o Dir::Etc::sourcelist="sources.list.d/docker.list" -o Dir::Etc::sourceparts="-" '
         '-o APT::Get::List-Cleanup="0"')
    sudo('apt-get -y install docker-engine')
    if not skip_group_assignment:
        assign_user_groups(env.user, ['docker'])


@task
def install_docker_centos(skip_group_assignment=False):
    """
    Installs Docker on a remote machine running CentOS and adds the current user to the ``docker`` user group.

    :param skip_group_assignment: If set to ``True``, skips the assignment to the ``docker`` group.
    :type skip_group_assignment: bool
    """
    sudo("tee /etc/yum.repos.d/docker.repo <<-'EOF'\n"
         "[dockerrepo]\n"
         "name=Docker Repository\n"
         "baseurl=https://yum.dockerproject.org/repo/main/centos/$releasever/\n"
         "enabled=1\n"
         "gpgcheck=1\n"
         "gpgkey=https://yum.dockerproject.org/gpg\n"
         "EOF\n")
    sudo('yum install -y docker-engine')
    if not skip_group_assignment:
        assign_user_groups(env.user, ['docker'])


def _build_socat():
    with temp_dir() as remote_tmp:
        socat_version = env.get('socat_version', DEFAULT_SOCAT_VERSION)
        src_dir = '{0}/socat-{1}'.format(remote_tmp, socat_version)
        src_file = '.'.join((src_dir, 'tar.gz'))
        run(curl(SOCAT_URL.format(socat_version), src_file))
        run(untargz(src_file, remote_tmp))
        with cd(src_dir):
            run('./configure')
            run('make')
            sudo('make install')


@task
def build_socat_ubuntu():
    """
    Downloads and installs the tool `socat` from source on Ubuntu.
    """
    sudo('apt-get update')
    sudo('apt-get -y install gcc make')
    _build_socat()


@task
def build_socat_centos():
    """
    Downloads and installs the tool `socat` from source on CentOS.
    """
    sudo('yum install -y gcc make')
    _build_socat()


@task
@runs_once
def fetch_socat(local):
    """
    Fetches the `socat` binary from a remote host.

    :param local: Local path to copy the file to, or local file path.
    :type local: unicode
    """
    remote_file = '/usr/local/bin/socat'
    local_file = expand_path(local)
    if os.path.exists(local_file) and not os.path.isfile(local_file):
        local_file = os.path.join(local, 'socat')
    get(remote_file, local_file)


@task
def install_socat(src):
    """
    Places the `socat` binary on a remote host.

    :param src: Local directory that contains the source file, or path to the file itself.
    :type src: unicode
    """
    src_file = expand_path(src)
    if os.path.exists(src_file) and not os.path.isfile(src_file):
        src_file = os.path.join(src_file, 'socat')
        if not os.path.exists(src_file):
            error("Socat cannot be found in the provided path ({0} or {1}).".format(src, src_file))
    dest_file = '/usr/local/bin/socat'
    put(src_file, dest_file, use_sudo=True, mode='0755')


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
def cleanup_containers(include_initial=False):
    """
    Removes all containers that have finished running.
    """
    docker_fabric().cleanup_containers(include_initial=include_initial)


@task
def cleanup_images(remove_old=False):
    """
    Removes all images that have no name, and that are not references as dependency by any other named image.

    :param remove_old: Also remove images that do have a name, but no `latest` tag.
    :type remove_old: bool
    """
    keep_tags = env.get('docker_keep_tags')
    docker_fabric().cleanup_images(remove_old=remove_old, keep_tags=keep_tags)


@task
def remove_all_containers():
    """
    Stops and removes all containers from the remote. Use with caution outside of a development environment!
    :return:
    """
    docker_fabric().remove_all_containers()


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
