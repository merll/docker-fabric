# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from fabric.api import task
from fabric.utils import error

from .apiclient import container_fabric


@task
def perform(action_name, map_name, config_name):
    cf = container_fabric()
    cf_method = getattr(cf, action_name)
    if callable(cf_method):
        cf_method(config_name, map_name=map_name)
    else:
        error("Action '{0}' is not available or not a valid method.".format(action_name))


@task
def create(map_name, config_name, instances=None, **kwargs):
    container_fabric().create(config_name, instances=instances, map_name=map_name, **kwargs)


@task
def start(map_name, config_name, instances=None, **kwargs):
    container_fabric().start(config_name, instances=instances, map_name=map_name, **kwargs)


@task
def stop(map_name, config_name, instances=None, **kwargs):
    container_fabric().stop(config_name, instances=instances, map_name=map_name, **kwargs)


@task
def remove(map_name, config_name, instances=None, **kwargs):
    container_fabric().remove(config_name, instances=instances, map_name=map_name, **kwargs)


@task
def startup(map_name, config_name, instances=None, **kwargs):
    container_fabric().startup(config_name, instances=instances, map_name=map_name, **kwargs)


@task
def shutdown(map_name, config_name, instances=None, **kwargs):
    container_fabric().shutdown(config_name, instances=instances, map_name=map_name, **kwargs)


@task
def update(map_name, config_name, instances=None, **kwargs):
    container_fabric().update(config_name, instances=instances, map_name=map_name, **kwargs)
