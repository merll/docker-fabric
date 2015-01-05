# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import ctypes
import multiprocessing


port_offset = multiprocessing.Value(ctypes.c_ulong)


class ConnectionDict(dict):
    def get(self, k, d, *args, **kwargs):
        e = super(ConnectionDict, self).get(k)
        if e is None:
            e = d(*args, **kwargs)
            self[k] = e
        return e


def get_local_port(init_port):
    with port_offset.get_lock():
        current_offset = port_offset.value
        port_offset.value += 1
    return int(init_port) + current_offset
