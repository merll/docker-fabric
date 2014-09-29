# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os
from fabric.api import cd, env, get, put, run, sudo, task
from fabric.utils import error

from dockermap.shortcuts import curl, untargz
from dockermap.utils import expand_path
from utils.files import temp_dir
from utils.net import get_ip4_address, get_ip6_address
from utils.users import assign_user_groups
from . import DEFAULT_SOCAT_VERSION, cli
from .apiclient import docker_fabric


SOCAT_URL = 'http://www.dest-unreach.org/socat/download/socat-{0}.tar.gz'


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
def check_version():
    print(docker_fabric().version())


@task
def get_ip(interface_name='docker0'):
    print(get_ip4_address(interface_name))


@task
def get_ipv6(interface_name='docker0', expand=False):
    print(get_ip6_address(interface_name, expand=expand))


@task
def list_images():
    print(docker_fabric().images())


@task
def list_containers(all=True):
    print(docker_fabric().containers(all=all))


@task
def cleanup_containers():
    docker_fabric().cleanup_containers()


@task
def cleanup_images():
    docker_fabric().cleanup_images()


@task
def remove_all_containers():
    docker_fabric().remove_all_containers()


@task
def save_image(image, filename=None):
    local_name = filename or '{0}.tar.gz'.format(image)
    cli.save_image(image, local_name)


@task
def load_image(filename):
    with open(filename, 'r') as f:
        docker_fabric().load_image(f)
