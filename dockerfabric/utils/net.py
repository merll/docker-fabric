# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json
from itertools import repeat

from invoke import Exit

from .output import stdout_result


IP4_FAMILY = 'inet'
IP6_FAMILY = 'inet6'


def _get_address(c, interface_name, family, scope):
    out = stdout_result(c, 'ip -j address'.format(interface_name), (1,), shell=False, quiet=True)
    parsed = json.loads(out)
    item = [i
            for i in parsed
            if i['ifname'] == interface_name]
    if not item:
        raise Exit("Network interface {0} not found.".format(interface_name))
    addr_info = [a
                 for a in item[0]['addr_info']
                 if a['scope'] == scope and a['family'] == family]
    if not addr_info:
        raise Exit("No {0} address found for interface {1} and scope {2}.".format(family, interface_name, scope))
    return addr_info[0]['local']


def _expand_groups(address):
    for group in address.split(':'):
        if group:
            yield group.zfill(4)
        else:
            zero_groups = 8 - address.count(':') if '::' in address else 0
            for z in repeat('0000', zero_groups):
                yield z


def get_ip4_address(c, interface_name, scope='global'):
    """
    Extracts the IPv4 address for a particular interface from `ifconfig`.

    :param c: Fabric connection.
    :type c: fabric.connection.Connection
    :param interface_name: Name of the network interface (e.g. ``eth0``).
    :type interface_name: unicode | str
    :param scope: Address scope.
    :type scope: str
    :return: IPv4 address; ``None`` if the interface is present but no address could be extracted.
    :rtype: unicode | str
    """
    return _get_address(c, interface_name, IP4_FAMILY, scope)


def get_ip6_address(c, interface_name, scope='global', expand=False):
    """
    Extracts the IPv6 address for a particular interface from `ifconfig`.

    :param c: Fabric connection.
    :type c: fabric.connection.Connection
    :param interface_name: Name of the network interface (e.g. ``eth0``).
    :type interface_name: unicode | str
    :param scope: Address scope.
    :type scope: str
    :param expand: If set to ``True``, an abbreviated address is expanded to the full address.
    :type expand: bool
    :return: IPv6 address; ``None`` if the interface is present but no address could be extracted.
    :rtype: unicode | str
    """
    address = _get_address(c, interface_name, IP6_FAMILY, scope)
    if address and expand:
        return ':'.join(_expand_groups(address))
    return address
