# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from itertools import repeat
import re

from fabric.utils import error
from .output import stdout_result


IP4_PATTERN = re.compile(r'\s+inet addr:\s*((?:\d{1,3}\.){3}\d{1,3})')
IP6_PATTERN = re.compile(r'\s+inet6 addr:\s*((?:[a-f0-9]{1,4}::?){1,7}[a-f0-9]{1,4})')


def _get_address(interface_name, pattern):
    out = stdout_result('ifconfig {0}'.format(interface_name), (1,), shell=False, quiet=True)
    if not out:
        error("Network interface {0} not found.".format(interface_name))
    match = pattern.search(out)
    if match:
        return match.group(1)
    return None


def _expand_groups(address):
    for group in address.split(':'):
        if group:
            yield group.zfill(4)
        else:
            zero_groups = 8 - address.count(':') if '::' in address else 0
            for z in repeat('0000', zero_groups):
                yield z


def get_ip4_address(interface_name):
    """
    Extracts the IPv4 address for a particular interface from `ifconfig`.

    :param interface_name: Name of the network interface (e.g. ``eth0``).
    :type interface_name: unicode
    :return: IPv4 address; ``None`` if the interface is present but no address could be extracted.
    :rtype: unicode
    """
    return _get_address(interface_name, IP4_PATTERN)


def get_ip6_address(interface_name, expand=False):
    """
    Extracts the IPv6 address for a particular interface from `ifconfig`.

    :param interface_name: Name of the network interface (e.g. ``eth0``).
    :type interface_name: unicode
    :param expand: If set to ``True``, an abbreviated address is expanded to the full address.
    :type expand: bool
    :return: IPv6 address; ``None`` if the interface is present but no address could be extracted.
    :rtype: unicode
    """
    address = _get_address(interface_name, IP6_PATTERN)
    if address and expand:
        return ':'.join(_expand_groups(address))
    return address
