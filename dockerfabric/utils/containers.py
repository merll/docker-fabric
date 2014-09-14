# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from fabric.context_managers import documented_contextmanager
from dockerfabric.apiclient import docker_fabric


@documented_contextmanager
def temp_container(image, no_op_cmd='/bin/true', create_kwargs={}, start_kwargs={}):
    df = docker_fabric()
    if create_kwargs:
        create_kwargs = create_kwargs.copy()
    if start_kwargs:
        start_kwargs = start_kwargs.copy()
    create_kwargs.update(entrypoint=no_op_cmd)
    start_kwargs.update(restart_policy=None)
    container = df.create_container(image, **create_kwargs)['Id']
    df.start(container, **start_kwargs)
    df.wait(container)
    yield container
    df.remove_container(container)
