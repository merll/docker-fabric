# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from datetime import datetime
import itertools
import os
from fabric.api import cd, env, get, put, run, sudo, task
from fabric.utils import error
import six

from dockermap.shortcuts import curl, untargz
from dockermap.utils import expand_path
from utils.files import temp_dir
from utils.net import get_ip4_address, get_ip6_address
from utils.users import assign_user_groups
from . import DEFAULT_SOCAT_VERSION, cli
from .apiclient import docker_fabric


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

    rows = [[_get_column(i, col) for col in columns] for i in data_dict]
    col_lens = map(max, (map(_max_len, c) for c in zip(*rows)))
    row_format = '  '.join('{{{0}:{1}}}'.format(i, l) for i, l in enumerate(col_lens))
    print(row_format.format(*columns))
    for row in rows:
        for c in itertools.izip_longest(*row, fillvalue=''):
            print(row_format.format(*c))


@task
def install_docker():
    sudo('apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys 36A1D7869245C8950F966E92D8576A8BA88D21E9')
    sudo('echo deb https://get.docker.io/ubuntu docker main > /etc/apt/sources.list.d/docker.list')
    sudo('apt-get update')
    sudo('apt-get -y install lxc-docker')
    assign_user_groups(env.user, ['docker'])


@task
def build_socat():
    sudo('apt-get update')
    sudo('apt-get -y install gcc make')
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
def fetch_socat(local):
    remote_file = '/usr/local/bin/socat'
    local_file = expand_path(local)
    if os.path.exists(local_file) and not os.path.isfile(local_file):
        local_file = os.path.join(local, 'socat')
    get(remote_file, local_file)


@task
def install_socat(src):
    src_file = expand_path(src)
    if os.path.exists(src_file) and not os.path.isfile(src_file):
        src_file = os.path.join(src_file, 'socat')
        if not os.path.exists(src_file):
            error("Socat cannot be found in the provided path ({0} or {1}).".format(src, src_file))
    dest_file = '/usr/local/bin/socat'
    put(src_file, dest_file, use_sudo=True, mode='0755')


@task
def version():
    output = docker_fabric().version()
    col_len = max(map(len, output.keys())) + 1
    for k, v in six.iteritems(output):
        print('{0:{1}} {2}'.format(''.join((k, ':')), col_len, v))


@task
def get_ip(interface_name='docker0'):
    print(get_ip4_address(interface_name))


@task
def get_ipv6(interface_name='docker0', expand=False):
    print(get_ip6_address(interface_name, expand=expand))


@task
def list_images(list_all=False, full_ids=False):
    images = docker_fabric().images(all=list_all)
    _format_output_table(images, IMAGE_COLUMNS, full_ids)


@task
def list_containers(list_all=True, short_image=True, full_ids=False, full_cmd=False):
    containers = docker_fabric().containers(all=list_all)
    _format_output_table(containers, CONTAINER_COLUMNS, full_ids, full_cmd, short_image)


@task
def cleanup_containers():
    docker_fabric().cleanup_containers()


@task
def cleanup_images(remove_old=False):
    docker_fabric().cleanup_images(remove_old)


@task
def remove_all_containers():
    docker_fabric().remove_all_containers()


@task
def save_image(image, filename=None):
    local_name = filename or '{0}.tar.gz'.format(image)
    cli.save_image(image, local_name)


@task
def load_image(filename, timeout=120):
    c = docker_fabric()
    with open(expand_path(filename), 'r') as f:
        _timeout = c._timeout
        c._timeout = timeout
        try:
            c.load_image(f)
        finally:
            c._timeout = _timeout
