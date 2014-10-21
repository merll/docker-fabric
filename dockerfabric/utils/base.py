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
