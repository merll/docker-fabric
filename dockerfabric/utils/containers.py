# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from fabric.context_managers import documented_contextmanager
from dockerfabric.apiclient import docker_fabric


@documented_contextmanager
def temp_container(image, no_op_cmd='/bin/true', create_kwargs=None, start_kwargs=None):
    """
    Creates a temporary container, which can be used e.g. for copying resources. The container is removed once it
    is no longer needed. Note that ``no_op_cmd`` needs to be set appropriately, since the method will wait for the
    container to finish before copying resources.

    :param image: Image name or id to create the container from.
    :type image: unicode
    :param no_op_cmd: Dummy-command to run, only for being able to access the container.
    :type no_op_cmd: unicode
    :param create_kwargs: Additional kwargs for creating the container. The ``entrypoint`` will be set to ``no_op_cmd``.
    :type create_kwargs: dict
    :param start_kwargs: Additional kwargs for starting the container. ``restart_policy`` will be set to ``None``.
    :type start_kwargs: dict
    :return: Id of the temporary container.
    :rtype: unicode
    """
    df = docker_fabric()
    create_kwargs = create_kwargs.copy() if create_kwargs else dict()
    start_kwargs = start_kwargs.copy() if start_kwargs else dict()
    create_kwargs.update(entrypoint=no_op_cmd)
    start_kwargs.update(restart_policy=None)
    container = df.create_container(image, **create_kwargs)['Id']
    df.start(container, **start_kwargs)
    df.wait(container)
    yield container
    df.remove_container(container)
