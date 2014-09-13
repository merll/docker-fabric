# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

from fabric.api import env
# noinspection PyUnresolvedReferences
from dockermap.map.yaml import yaml, load_file, load_map, load_map_file


def expand_env(loader, node):
    val = loader.construct_scalar(node)
    return env[val]


yaml.add_constructor('!env', expand_env, yaml.SafeLoader)
