# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os
import posixpath

import yaml
from fabric import task
from invoke.exceptions import Exit
from six import iteritems

from dockermap.map.action import ContainerUtilAction
from .api import container_fabric
from .utils.files import temp_dir


@task
def perform(c, action_name, container, **kwargs):
    """
    Performs an action on the given container map and configuration.

    :param c: Connection
    :param action_name: Name of the action (e.g. ``update``).
    :param container: Container configuration name.
    :param kwargs: Keyword arguments for the action implementation.
    """
    cf = container_fabric(c)
    cf.call(action_name, container, **kwargs)


@task
def create(c, container, **kwargs):
    """
    Creates a container and its dependencies.

    :param c: Connection
    :param container: Container configuration name.
    :param kwargs: Keyword arguments to the action implementation.
    """
    container_fabric(c).create(container, **kwargs)


@task
def start(c, container, **kwargs):
    """
    Starts a container and its dependencies.

    :param c: Connection
    :param container: Container configuration name.
    :param kwargs: Keyword arguments to the action implementation.
    """
    container_fabric(c).start(container, **kwargs)


@task
def stop(c, container, **kwargs):
    """
    Stops a container and its dependents.

    :param c: Connection
    :param container: Container configuration name.
    :param kwargs: Keyword arguments to the action implementation.
    """
    container_fabric(c).stop(container, **kwargs)


@task
def remove(c, container, **kwargs):
    """
    Removes a container and its dependents.

    :param c: Connection
    :param container: Container configuration name.
    :param kwargs: Keyword arguments to the action implementation.
    """
    container_fabric(c).remove(container, **kwargs)


@task
def restart(c, container, **kwargs):
    """
    Restarts a container and starts its dependencies if necessary.

    :param c: Connection
    :param container: Container configuration name.
    :param kwargs: Keyword arguments to the action implementation.
    """
    container_fabric(c).restart(container, **kwargs)


@task
def startup(c, container, **kwargs):
    """
    Creates and starts a container and its dependencies.

    :param c: Connection
    :param container: Container configuration name.
    :param kwargs: Keyword arguments to the action implementation.
    """
    container_fabric(c).startup(container, **kwargs)


@task
def shutdown(c, container, **kwargs):
    """
    Stops and removes a container and its dependents.

    :param c: Connection
    :param container: Container configuration name.
    :param kwargs: Keyword arguments to the action implementation.
    """
    container_fabric(c).shutdown(container, **kwargs)


@task
def update(c, container, **kwargs):
    """
    Updates a container and its dependencies. Creates and starts containers as necessary.

    :param c: Connection
    :param container: Container configuration name.
    :param kwargs: Keyword arguments to the action implementation.
    """
    container_fabric(c).update(container, **kwargs)


@task
def kill(c, container, **kwargs):
    """
    Sends a signal to a container, by default ``SIGKILL``. You can also pass a different signal such as ``SIGHUP``.

    :param c: Connection
    :param container: Container configuration name.
    :param kwargs: Keyword arguments to the action implementation.
    """
    container_fabric(c).signal(container, **kwargs)


@task
def pull_images(c, container, **kwargs):
    """
    Pulls missing images, including dependencies.

    :param c: Connection
    :param container: Container configuration name.
    :param kwargs: Keyword arguments to the action implementation.
    """
    container_fabric(c).pull_images(container, **kwargs)


@task
def script(c, container, script_path, fail_nonzero=False, upload_dir=False, **kwargs):
    """
    Runs a script inside a container, which is created with all its dependencies. The container is removed after it
    has been run, whereas the dependencies are not destroyed. The output is printed to the console.

    :param c: Connection
    :param container: Container configuration name.
    :param script_path: Local path to the script file.
    :param fail_nonzero: Fail if the script returns with a nonzero exit code.
    :param upload_dir: Upload the entire parent directory of the script file to the remote.
    :param kwargs: Additional keyword arguments to the run_script action.
    """
    full_script_path = os.path.abspath(script_path)
    prefix, name = os.path.split(full_script_path)
    with temp_dir(c) as remote_tmp:
        if upload_dir:
            prefix_path, prefix_name = os.path.split(prefix)
            remote_script = posixpath.join(remote_tmp, prefix_name, name)
            c.put(prefix, remote_tmp, mirror_local_mode=True)
        else:
            remote_script = posixpath.join(remote_tmp, name)
            c.put(script_path, remote_script, mirror_local_mode=True)
        results = [output.result
                   for output in container_fabric(c).run_script(container, script_path=remote_script, **kwargs)
                   if output.action_type == ContainerUtilAction.SCRIPT]
    for res in results:
        if res['exit_code'] == 0 or not fail_nonzero:
            return res['log']
        raise Exit(res['log'], res['exit_code'])


@task
def single_cmd(c, container, command, fail_nonzero=False, download_result=None, **kwargs):
    """
    Runs a script inside a container, which is created with all its dependencies. The container is removed after it
    has been run, whereas the dependencies are not destroyed. The output is printed to the console.

    :param c: Connection
    :param container: Container configuration name.
    :param command: Command line to run.
    :param fail_nonzero: Fail if the script returns with a nonzero exit code.
    :param download_result: Download any results that the command has written back to a temporary directory.
    :param kwargs: Additional keyword arguments to the run_script action.
    """
    with temp_dir(c) as remote_tmp:
        kwargs.setdefault('command_format', ['-c', command])
        results = [output.result
                   for output in container_fabric(c).run_script(container, script_path=remote_tmp, **kwargs)
                   if output.action_type == ContainerUtilAction.SCRIPT]
        if download_result:
            c.get(posixpath.join(remote_tmp, '*'), local_path=download_result)
    for res in results:
        if res['exit_code'] == 0 or not fail_nonzero:
            return res['log']
        raise Exit(res['log'], res['exit_code'])


@task
def show(c, map_name=None):
    all_maps = container_fabric(c).maps
    if map_name:
        data = all_maps[map_name].as_dict()
    else:
        data = {k: v.as_dict()
                for k, v in iteritems(all_maps)}
    return yaml.safe_dump(data, default_flow_style=False, canonical=False)
