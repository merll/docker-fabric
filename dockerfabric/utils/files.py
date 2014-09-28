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
    """
    Creates a temporary directory on the remote end. Uses the command ``mktemp`` to do so.

    :return: Path to the temporary directory.
    :rtype: unicode
    """
    return single_line_stdout('mktemp -d')


def remove_ignore(path, use_sudo=False):
    """
    Recursively removes a file or directory, ignoring any errors that may occur. Should only be used for temporary
    files that can be assumed to be cleaned up at a later point.

    :param path: Path to file or directory to remove.
    :type path: unicode
    :param use_sudo: Use the `sudo` command.
    :type use_sudo: bool
    """
    which = sudo if use_sudo else run
    which(rm(path, recursive=True), warn_only=True)


def is_directory(path, use_sudo=False):
    """
    Check if the remote path exists and is a directory.

    :param path: Remote path to check.
    :type path: unicode
    :param use_sudo: Use the `sudo` command.
    :type use_sudo: bool
    :return: `True` if the path exists and is a directory; `False` if it exists, but is a file; `None` if it does not
      exist.
    :rtype: bool or ``None``
    """
    result = single_line_stdout('if [[ -f {0} ]]; then echo 0; elif [[ -d {0} ]]; then echo 1; else echo -1; fi'.format(path), sudo=use_sudo, quiet=True)
    if result == '0':
        return False
    elif result == '1':
        return True
    else:
        return None


@documented_contextmanager
def temp_dir(apply_chown=None, apply_chmod=None):
    """
    Creates a temporary directory on the remote machine. The directory is removed when no longer needed. Failure to do
    so will be ignored.

    :param apply_chown: Optional; change the owner of the directory.
    :type apply_chown: bool
    :param apply_chmod: Optional; change the permissions of the directory.
    :type apply_chmod: bool
    :return: Path to the temporary directory.
    :rtype: unicode
    """
    path = get_remote_temp()
    if apply_chmod:
        run(chmod(apply_chmod, path))
    if apply_chown:
        sudo(chown(apply_chown, path))
    yield path
    remove_ignore(path, True)


@documented_contextmanager
def local_temp_dir():
    """
    Creates a local temporary directory. The directory is removed when no longer needed. Failure to do
    so will be ignored.

    :return: Path to the temporary directory.
    :rtype: unicode
    """
    path = tempfile.mkdtemp()
    yield path
    shutil.rmtree(path, ignore_errors=True)


def extract_tar(filename, dest_path, **kwargs):
    """
    Extracts a TAR archive. All element names starting with ``/`` (indicating an absolute path) or that contain ``..``
    as references to a parent directory are not extracted.

    :param filename: Path to the tar file.
    :type filename: unicode
    :param dest_path: Destination path to extract the contents to.
    :type dest_path: unicode
    :param kwargs: Additional kwargs for opening the TAR file (:func:`tarfile.open`).
    """
    with tarfile.open(filename, 'r', **kwargs) as tf:
        safe_members = [name for name in tf.getmembers() if _safe_name(name)]
        if safe_members:
            tf.extractall(dest_path, safe_members)
