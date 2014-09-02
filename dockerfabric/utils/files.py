# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import shutil
import tarfile
import tempfile

from fabric.api import run, sudo
from fabric.context_managers import documented_contextmanager

from dockermap.shortcuts import rm, chmod, chown
from .output import single_line_stdout


_safe_name = lambda tarinfo: tarinfo.name[0] != '/' and not '..' in tarinfo.name


def get_remote_temp():
    return single_line_stdout('mktemp -d')


def remove_ignore(path, use_sudo=False):
    which = sudo if use_sudo else run
    try:
        which(rm(path, recursive=True))
    except OSError:
        pass


def is_directory(path, use_sudo=False):
    result = single_line_stdout('if [[ -f {0} ]]; then echo 0; elif [[ -d {0} ]]; then echo 1; else echo -1; fi'.format(path), sudo=use_sudo, quiet=True)
    if result == '0':
        return False
    elif result == '1':
        return True
    else:
        return None


@documented_contextmanager
def temp_dir(apply_chown=None, apply_chmod=None):
    path = get_remote_temp()
    if apply_chmod:
        run(chmod(apply_chmod, path))
    if apply_chown:
        sudo(chown(apply_chown, path))
    yield path
    remove_ignore(path, True)


@documented_contextmanager
def local_temp_dir():
    path = tempfile.mkdtemp()
    yield path
    shutil.rmtree(path, ignore_errors=True)


def extract_tar(filename, dest_path, **kwargs):
    with tarfile.open(filename, 'r', **kwargs) as tf:
        safe_members = [name for name in tf.getmembers() if _safe_name(name)]
        if safe_members:
            tf.extractall(dest_path, safe_members)
