# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from itertools import repeat
import re

from .output import stdout_result


IP4_PATTERN = re.compile(r'\s+inet addr:\s*((?:\d{1,3}\.){3}\d{1,3})')
IP6_PATTERN = re.compile(r'\s+inet6 addr:\s*((?:[a-f0-9]{1,4}::?){1,7}[a-f0-9]{1,4})')


def _expand_groups(address):
    for group in address.split(':'):
        if group:
            yield group.zfill(4)
        else:
            zero_groups = 8 - address.count(':') if '::' in address else 0
            for z in repeat('0000', zero_groups):
                yield z


def get_ip4_address(interface_name):
    out = stdout_result('ifconfig {0}'.format(interface_name), shell=False, quiet=True)
    match = IP4_PATTERN.search(out)
    if match:
        return match.group(1)
    return None


def get_ip6_address(interface_name, expand=False):
    out = stdout_result('ifconfig {0}'.format(interface_name), shell=False, quiet=True)
    match = IP6_PATTERN.search(out)
    if match:
        address = match.group(1)
        if expand:
            return ':'.join(_expand_groups(address))
        return address
    return None
