# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

from fabric.api import env
from dockermap.functional import lazy_once
# noinspection PyUnresolvedReferences
from dockermap.map.yaml import (yaml, load_file, load_map, load_map_file,
                                load_clients as _load_clients,
                                load_clients_file as _load_clients_file)
from .apiclient import DockerClientConfiguration


env_get = lambda v: env[v]


def expand_env_lazy(loader, node):
    """
    Substitutes a variable read from a YAML node with the value stored in Fabric's ``env`` dictionary. Creates an
    object for late resolution.

    :param loader: YAML loader.
    :type loader: yaml.loader.SafeLoader
    :param node: Document node.
    :type node: ScalarNode
    :return: Corresponding value stored in the ``env`` dictionary.
    :rtype: any
    """
    val = loader.construct_scalar(node)
    return lazy_once(env_get, val)


def expand_env(loader, node):
    """
    Substitutes a variable read from a YAML node with the value stored in Fabric's ``env`` dictionary.

    :param loader: YAML loader.
    :type loader: yaml.loader.SafeLoader
    :param node: Document node.
    :type node: ScalarNode
    :return: Corresponding value stored in the ``env`` dictionary.
    :rtype: any
    """
    val = loader.construct_scalar(node)
    return env[val]


def load_clients(stream):
    """
    Loads client configurations from a YAML document stream.

    :param stream: YAML stream.
    :type stream: file
    :return: A dictionary of client configuration objects.
    :rtype: dict[unicode, dockerfabric.apiclient.DockerClientConfiguration]
    """
    return _load_clients(stream, configuration_class=DockerClientConfiguration)


def load_clients_file(filename):
    """
    Loads client configurations from a YAML file.

    :param filename: YAML file name.
    :type filename: unicode
    :return: A dictionary of client configuration objects.
    :rtype: dict[unicode, dockerfabric.apiclient.DockerClientConfiguration]
    """
    return _load_clients_file(filename, configuration_class=DockerClientConfiguration)


yaml.add_constructor('!env_lazy', expand_env_lazy, yaml.SafeLoader)
yaml.add_constructor('!env', expand_env, yaml.SafeLoader)
