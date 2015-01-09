# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import six

from fabric.api import env
from fabric.network import needs_host


@needs_host
def get_current_roles():
    """
    Determines the list of roles, that the current host is assigned to. If ``env.roledefs`` is not set, an empty list
    is returned.

    :return: List of roles of the current host.
    :rtype: list
    """
    current_host = env.host_string
    roledefs = env.get('roledefs')
    if roledefs:
        return [role for role, hosts in six.iteritems(roledefs) if current_host in hosts]
    return []


def get_role_addresses(role_name, interface_name):
    roledefs = env.get('roledefs')
    clients = env.get('docker_clients')
    if roledefs and clients:
        role_hosts = roledefs.get(role_name)
        if role_hosts:
            return set(client_config.interfaces[interface_name]
                       for client_name, client_config in six.iteritems(clients)
                       if client_config.get('fabric_host') in role_hosts)
    return set()
