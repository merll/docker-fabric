# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os
import posixpath

from fabric.api import get, put, puts, task
from fabric.utils import error
import six

from .apiclient import container_fabric
from .utils.files import temp_dir


@task
def perform(action_name, map_name, config_name, **kwargs):
    """
    Performs an action on the given container map and configuration.

    :param action_name: Name of the action (e.g. ``update``).
    :param map_name: Container map name.
    :param config_name: Container configuration name.
    :param kwargs: Keyword arguments for the action implementation.
    """
    cf = container_fabric()
    cf.call(action_name, config_name, map_name=map_name, **kwargs)


@task
def create(map_name, config_name, instances=None, **kwargs):
    """
    Creates a container and its dependencies.

    :param map_name: Container map name.
    :param config_name: Container configuration name.
    :param instances: Optional instance names.
    :param kwargs: Keyword arguments to the action implementation.
    """
    container_fabric().create(config_name, instances=instances, map_name=map_name, **kwargs)


@task
def start(map_name, config_name, instances=None, **kwargs):
    """
    Starts a container and its dependencies.

    :param map_name: Container map name.
    :param config_name: Container configuration name.
    :param instances: Optional instance names.
    :param kwargs: Keyword arguments to the action implementation.
    """
    container_fabric().start(config_name, instances=instances, map_name=map_name, **kwargs)


@task
def stop(map_name, config_name, instances=None, **kwargs):
    """
    Stops a container and its dependents.

    :param map_name: Container map name.
    :param config_name: Container configuration name.
    :param instances: Optional instance names.
    :param kwargs: Keyword arguments to the action implementation.
    """
    container_fabric().stop(config_name, instances=instances, map_name=map_name, **kwargs)


@task
def remove(map_name, config_name, instances=None, **kwargs):
    """
    Removes a container and its dependents.

    :param map_name: Container map name.
    :param config_name: Container configuration name.
    :param instances: Optional instance names.
    :param kwargs: Keyword arguments to the action implementation.
    """
    container_fabric().remove(config_name, instances=instances, map_name=map_name, **kwargs)


@task
def restart(map_name, config_name, instances=None, **kwargs):
    """
    Restarts a container and starts its dependencies if necessary.

    :param map_name: Container map name.
    :param config_name: Container configuration name.
    :param instances: Optional instance names.
    :param kwargs: Keyword arguments to the action implementation.
    """
    container_fabric().restart(config_name, instances=instances, map_name=map_name, **kwargs)


@task
def startup(map_name, config_name, instances=None, **kwargs):
    """
    Creates and starts a container and its dependencies.

    :param map_name: Container map name.
    :param config_name: Container configuration name.
    :param instances: Optional instance names.
    :param kwargs: Keyword arguments to the action implementation.
    """
    container_fabric().startup(config_name, instances=instances, map_name=map_name, **kwargs)


@task
def shutdown(map_name, config_name, instances=None, **kwargs):
    """
    Stops and removes a container and its dependents.

    :param map_name: Container map name.
    :param config_name: Container configuration name.
    :param instances: Optional instance names.
    :param kwargs: Keyword arguments to the action implementation.
    """
    container_fabric().shutdown(config_name, instances=instances, map_name=map_name, **kwargs)


@task
def update(map_name, config_name, instances=None, **kwargs):
    """
    Updates a container and its dependencies. Creates and starts containers as necessary.

    :param map_name: Container map name.
    :param config_name: Container configuration name.
    :param instances: Optional instance names.
    :param kwargs: Keyword arguments to the action implementation.
    """
    container_fabric().update(config_name, instances=instances, map_name=map_name, **kwargs)


@task
def script(map_name, config_name, script_path, fail_nonzero=False, upload_dir=False, **kwargs):
    """
    Runs a script inside a container, which is created with all its dependencies. The container is removed after it
    has been run, whereas the dependencies are not destroyed. The output is printed to the console.

    :param map_name: Container map name.
    :param config_name: Container configuration name.
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
        results = container_fabric().run_script(config_name, map_name=map_name, script_path=remote_script, **kwargs)
        for client, res in six.iteritems(results):
            puts("Exit code: {0}".format(res['exit_code']))
            if res['exit_code'] == 0 or not fail_nonzero:
                puts(res['log'])
            else:
                error(res['log'])


@task
def single_cmd(map_name, config_name, command, fail_nonzero=False, download_result=None, **kwargs):
    """
    Runs a script inside a container, which is created with all its dependencies. The container is removed after it
    has been run, whereas the dependencies are not destroyed. The output is printed to the console.

    :param map_name: Container map name.
    :param config_name: Container configuration name.
    :param fail_nonzero: Fail if the script returns with a nonzero exit code.
    :param download_result: Download any results that the command has written back to a temporary directory.
    :param kwargs: Additional keyword arguments to the run_script action.
    """
    with temp_dir() as remote_tmp:
        if 'command_format' not in kwargs:
            kwargs['command_format'] = ['-c', command]
        results = container_fabric().run_script(config_name, map_name=map_name, script_path=remote_tmp, **kwargs)
        for client, res in six.iteritems(results):
            puts("Exit code: {0}".format(res['exit_code']))
            if res['exit_code'] == 0 or not fail_nonzero:
                puts(res['log'])
            else:
                error(res['log'])
            if download_result:
                get(posixpath.join(remote_tmp, '*'), local_path=download_result)
