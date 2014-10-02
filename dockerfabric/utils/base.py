# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import six

from fabric.api import env
from fabric.network import needs_host


@needs_host
def get_current_roles():
    current_host = env.host_string
    roledefs = env.get('roledefs')
    if roledefs:
        return [role for role, hosts in six.iteritems(roledefs) if current_host in hosts]
    return []
