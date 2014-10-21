# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

from fabric.api import env
# noinspection PyUnresolvedReferences
from dockermap.map.yaml import yaml, load_file, load_map, load_map_file


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


yaml.add_constructor('!env', expand_env, yaml.SafeLoader)
