# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os
import posixpath

from fabric.api import cd, get, run, sudo
from fabric.network import needs_host

from dockermap.shortcuts import chmod, chown, targz
from .utils.containers import temp_container
from .utils.files import temp_dir, is_directory


@needs_host
def copy_resource(container, resource, local_filename, contents_only=True):
    """
    Copies a resource from a container to a compressed tarball and downloads it.

    :param container:
    :param resource:
    :param local_filename:
    :param contents_only:
    :return:
    """
    with temp_dir() as remote_tmp:
        base_name = os.path.basename(resource)
        copy_path = posixpath.join(remote_tmp, 'copy_tmp')
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
def copy_resources(src_container, src_resources, storage_dir, dst_directories={}, apply_chown=None, apply_chmod=None):
    def _copy_resource(resource):
        default_dest_path = generic_path if generic_path is not None else resource
        dest_path = dst_directories.get(resource, default_dest_path).strip(posixpath.sep)
        head, tail = posixpath.split(dest_path)
        rel_path = posixpath.join(storage_dir, head)
        run('docker cp {0}:{1} {2}'.format(src_container, resource, rel_path), shell=False)

    generic_path = dst_directories.get('*')
    for res in src_resources:
        _copy_resource(res)
    if apply_chmod:
        run(chmod(apply_chmod, storage_dir))
    if apply_chown:
        sudo(chown(apply_chown, storage_dir))


@needs_host
def isolate_and_get(src_container, src_resources, local_dst_dir, **kwargs):
    with temp_dir() as remote_tmp:
        copy_path = posixpath.join(remote_tmp, 'copy_tmp')
        archive_path = posixpath.join(remote_tmp, 'container_{0}.tar.gz'.format(src_container))
        copy_resources(src_container, src_resources, copy_path, **kwargs)
        with cd(copy_path):
            sudo(targz(archive_path, '*'))
        get(archive_path, local_dst_dir)


@needs_host
def isolate_to_image(src_container, src_resources, dst_image, **kwargs):
    with temp_dir() as remote_tmp:
        copy_resources(src_container, src_resources, remote_tmp, **kwargs)
        with cd(remote_tmp):
            sudo('tar -cz * | docker import - {0}'.format(dst_image))


@needs_host
def save_image(image, local_filename):
    with temp_dir() as remote_tmp:
        archive = posixpath.join(remote_tmp, 'image_{0}.tar.gz'.format(image))
        run('docker save {0} | gzip --stdout > {1}'.format(image, archive), shell=False)
        get(archive, local_filename)


@needs_host
def flatten_image(image, dest_image=None, no_op_cmd='/bin/true', create_kwargs={}, start_kwargs={}):
    dest_image = dest_image or image
    with temp_container(image, no_op_cmd=no_op_cmd, create_kwargs=create_kwargs, start_kwargs=start_kwargs) as c:
        run('docker export {0} | docker import - {1}'.format(c, dest_image), shell=False)
