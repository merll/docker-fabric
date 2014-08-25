# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from fabric.api import cd, env, run, sudo, task

from dockermap.shortcuts import curl, untargz
from utils.files import temp_dir
from utils.users import assign_user_groups
from .apiclient import DockerFabricClient


SOCAT_URL = 'http://www.dest-unreach.org/socat/download/socat-{0}.tar.gz'


@task
def install_docker():
    sudo('apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys 36A1D7869245C8950F966E92D8576A8BA88D21E9')
    sudo('echo deb https://get.docker.io/ubuntu docker main > /etc/apt/sources.list.d/docker.list')
    sudo('apt-get update')
    sudo('apt-get -y install lxc-docker')
    assign_user_groups('$LOGNAME', ['docker'])


@task
def build_socat():
    with temp_dir() as remote_tmp:
        src_dir = '{0}/socat-{1}'.format(remote_tmp, env.socat_version)
        src_file = '.'.join((src_dir, 'tar.gz'))
        run(curl(SOCAT_URL.format(env.socat_version), src_file))
        run(untargz(src_file, remote_tmp))
        with cd(src_dir):
            run('./configure')
            run('make')
            sudo('make install')


@task
def check_version():
    with DockerFabricClient() as c:
        print(c.version())


@task
def list_images():
    with DockerFabricClient() as c:
        print(c.images())


@task
def list_containers(all=True):
    with DockerFabricClient() as c:
        print(c.containers(all=all))


@task
def cleanup_containers():
    with DockerFabricClient() as c:
        c.cleanup_containers()


@task
def cleanup_images():
    with DockerFabricClient() as c:
        c.cleanup_images()


@task
def remove_all_containers():
    with DockerFabricClient() as c:
        c.remove_all_containers()
