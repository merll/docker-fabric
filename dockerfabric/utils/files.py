# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import shutil
import tarfile
import tempfile
from contextlib import contextmanager

from dockermap.shortcuts import rm, chmod, chown
from .output import single_line_stdout


DIR_TEST_STR = 'if [[ -f {0} ]]; then echo 0; elif [[ -d {0} ]]; then echo 1; else echo -1; fi'


def _safe_name(tarinfo):
    return tarinfo.name[0] != '/' and '..' not in tarinfo.name


def get_remote_temp(c):
    """
    Creates a temporary directory on the remote end. Uses the command ``mktemp`` to do so.

    :param c: Fabric connection.
    :type c: fabric.connection.Connection
    :return: Path to the temporary directory.
    :rtype: unicode | str
    """
    return single_line_stdout(c, 'mktemp -d')


def remove_ignore(c, path, use_sudo=False, force=False):
    """
    Recursively removes a file or directory, ignoring any errors that may occur. Should only be used for temporary
    files that can be assumed to be cleaned up at a later point.

    :param c: Fabric connection.
    :type c: fabric.connection.Connection
    :param path: Path to file or directory to remove.
    :type path: unicode | str
    :param use_sudo: Use the `sudo` command.
    :type use_sudo: bool
    :param force: Force the removal.
    :type force: bool
    """
    which = c.sudo if use_sudo else c.run
    which(rm(path, recursive=True, force=force), warn=True)


def is_directory(c, path, use_sudo=False):
    """
    Check if the remote path exists and is a directory.

    :param c: Fabric connection.
    :type c: fabric.connection.Connection
    :param path: Remote path to check.
    :type path: unicode | str
    :param use_sudo: Use the `sudo` command.
    :type use_sudo: bool
    :return: `True` if the path exists and is a directory; `False` if it exists, but is a file; `None` if it does not
      exist.
    :rtype: bool | NoneType
    """
    result = single_line_stdout(c, DIR_TEST_STR.format(path), sudo=use_sudo, quiet=True)
    if result == '0':
        return False
    elif result == '1':
        return True
    else:
        return None


@contextmanager
def temp_dir(c, apply_chown=None, apply_chmod=None, remove_using_sudo=None, remove_force=False):
    """
    Creates a temporary directory on the remote machine. The directory is removed when no longer needed. Failure to do
    so will be ignored.

    :param c: Fabric connection.
    :type c: fabric.connection.Connection
    :param apply_chown: Optional; change the owner of the directory.
    :type apply_chown: unicode | str
    :param apply_chmod: Optional; change the permissions of the directory.
    :type apply_chmod: unicode | str
    :param remove_using_sudo: Use sudo for removing the directory. ``None`` (default) means it is used depending on
     whether ``apply_chown`` has been set.
    :type remove_using_sudo: bool | NoneType
    :param remove_force: Force the removal.
    :type remove_force: bool
    :return: Path to the temporary directory.
    :rtype: unicode | str
    """
    path = get_remote_temp(c)
    try:
        if apply_chmod:
            c.run(chmod(apply_chmod, path))
        if apply_chown:
            if remove_using_sudo is None:
                remove_using_sudo = True
            c.sudo(chown(apply_chown, path))
        yield path
    finally:
        remove_ignore(c, path, use_sudo=remove_using_sudo, force=remove_force)


@contextmanager
def local_temp_dir():
    """
    Creates a local temporary directory. The directory is removed when no longer needed. Failure to do
    so will be ignored.

    :return: Path to the temporary directory.
    :rtype: unicode | str
    """
    path = tempfile.mkdtemp()
    yield path
    shutil.rmtree(path, ignore_errors=True)


def extract_tar(filename, dest_path, **kwargs):
    """
    Extracts a TAR archive. All element names starting with ``/`` (indicating an absolute path) or that contain ``..``
    as references to a parent directory are not extracted.

    :param filename: Path to the tar file.
    :type filename: unicode | str
    :param dest_path: Destination path to extract the contents to.
    :type dest_path: unicode | str
    :param kwargs: Additional kwargs for opening the TAR file (:func:`tarfile.open`).
    """
    with tarfile.open(filename, 'r', **kwargs) as tf:
        safe_members = [name for name in tf.getmembers() if _safe_name(name)]
        if safe_members:
            tf.extractall(dest_path, safe_members)
