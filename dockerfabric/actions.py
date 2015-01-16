# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from fabric.api import task

from .apiclient import container_fabric


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
