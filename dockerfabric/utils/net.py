# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import re

from .output import stdout_result


IP4_PATTERN = re.compile(r'\s+inet addr:\s*((?:\d{1,3}\.){3}\d{1,3})')


def get_ip4_address(interface_name):
    out = stdout_result('ifconfig {0}'.format(interface_name), shell=False, quiet=True)
    match = IP4_PATTERN.search(out)
    if match:
        return match.group(1)
    return None
