# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os
import posixpath

from fabric.api import get, put, puts, task
from fabric.utils import error

from dockermap.map.action import ContainerUtilAction
from .apiclient import container_fabric
from .utils.files import temp_dir


@task
def perform(action_name, container, **kwargs):
    """
    Performs an action on the given container map and configuration.

    :param action_name: Name of the action (e.g. ``update``).
    :param container: Container configuration name.
    :param kwargs: Keyword arguments for the action implementation.
    """
    cf = container_fabric()
    cf.call(action_name, container, **kwargs)


@task
def create(container, **kwargs):
    """
    Creates a container and its dependencies.

    :param container: Container configuration name.
    :param kwargs: Keyword arguments to the action implementation.
    """
    container_fabric().create(container, **kwargs)


@task
def start(container, **kwargs):
    """
    Starts a container and its dependencies.

    :param container: Container configuration name.
    :param kwargs: Keyword arguments to the action implementation.
    """
    container_fabric().start(container, **kwargs)


@task
def stop(container, **kwargs):
    """
    Stops a container and its dependents.

    :param container: Container configuration name.
    :param kwargs: Keyword arguments to the action implementation.
    """
    container_fabric().stop(container, **kwargs)


@task
def remove(container, **kwargs):
    """
    Removes a container and its dependents.

    :param container: Container configuration name.
    :param kwargs: Keyword arguments to the action implementation.
    """
    container_fabric().remove(container, **kwargs)


@task
def restart(container, **kwargs):
    """
    Restarts a container and starts its dependencies if necessary.

    :param container: Container configuration name.
    :param kwargs: Keyword arguments to the action implementation.
    """
    container_fabric().restart(container, **kwargs)


@task
def startup(container, **kwargs):
    """
    Creates and starts a container and its dependencies.

    :param container: Container configuration name.
    :param kwargs: Keyword arguments to the action implementation.
    """
    container_fabric().startup(container, **kwargs)


@task
def shutdown(container, **kwargs):
    """
    Stops and removes a container and its dependents.

    :param container: Container configuration name.
    :param kwargs: Keyword arguments to the action implementation.
    """
    container_fabric().shutdown(container, **kwargs)


@task
def update(container, **kwargs):
    """
    Updates a container and its dependencies. Creates and starts containers as necessary.

    :param container: Container configuration name.
    :param kwargs: Keyword arguments to the action implementation.
    """
    container_fabric().update(container, **kwargs)


@task
def kill(container, **kwargs):
    """
    Sends a signal to a container, by default ``SIGKILL``. You can also pass a different signal such as ``SIGHUP``.

    :param container: Container configuration name.
    :param kwargs: Keyword arguments to the action implementation.
    """
    container_fabric().signal(container, **kwargs)


@task
def pull_images(container, **kwargs):
    """
    Pulls missing images, including dependencies.

    :param container: Container configuration name.
    :param kwargs: Keyword arguments to the action implementation.
    """
    container_fabric().pull_images(container, **kwargs)


@task
def script(container, script_path, fail_nonzero=False, upload_dir=False, **kwargs):
    """
    Runs a script inside a container, which is created with all its dependencies. The container is removed after it
    has been run, whereas the dependencies are not destroyed. The output is printed to the console.

    :param container: Container configuration name.
    :param script_path: Local path to the script file.
    :param fail_nonzero: Fail if the script returns with a nonzero exit code.
    :param upload_dir: Upload the entire parent directory of the script file to the remote.
    :param kwargs: Additional keyword arguments to the run_script action.
    """
    full_script_path = os.path.abspath(script_path)
    prefix, name = os.path.split(full_script_path)
    with temp_dir() as remote_tmp:
        if upload_dir:
            prefix_path, prefix_name = os.path.split(prefix)
            remote_script = posixpath.join(remote_tmp, prefix_name, name)
            put(prefix, remote_tmp, mirror_local_mode=True)
        else:
            remote_script = posixpath.join(remote_tmp, name)
            put(script_path, remote_script, mirror_local_mode=True)
        results = [output.result
                   for output in container_fabric().run_script(container, script_path=remote_script, **kwargs)
                   if o.action_type == ContainerUtilAction.SCRIPT]
    for res in results:
        puts("Exit code: {0}".format(res['exit_code']))
        if res['exit_code'] == 0 or not fail_nonzero:
            puts(res['log'])
        else:
            error(res['log'])


@task
def single_cmd(container, command, fail_nonzero=False, download_result=None, **kwargs):
    """
    Runs a script inside a container, which is created with all its dependencies. The container is removed after it
    has been run, whereas the dependencies are not destroyed. The output is printed to the console.

    :param container: Container configuration name.
    :param command: Command line to run.
    :param fail_nonzero: Fail if the script returns with a nonzero exit code.
    :param download_result: Download any results that the command has written back to a temporary directory.
    :param kwargs: Additional keyword arguments to the run_script action.
    """
    with temp_dir() as remote_tmp:
        kwargs.setdefault('command_format', ['-c', command])
        results = [output.result
                   for output in container_fabric().run_script(container, script_path=remote_tmp, **kwargs)
                   if o.action_type == ContainerUtilAction.SCRIPT]
        if download_result:
            get(posixpath.join(remote_tmp, '*'), local_path=download_result)
    for res in results:
        puts("Exit code: {0}".format(res['exit_code']))
        if res['exit_code'] == 0 or not fail_nonzero:
            puts(res['log'])
        else:
            error(res['log'])
