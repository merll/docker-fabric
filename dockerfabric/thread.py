# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import multiprocessing


lock = multiprocessing.RLock()


class ThreadDefaultDict(dict):
    def get(self, k, d):
        lock.acquire()
        try:
            e = super(ThreadDefaultDict, self).get(k)
            if e is None:
                e = d()
                self[k] = e
        finally:
            lock.release()
        return e


class LocalPortCounter(object):
    def __init__(self):
        self._offset = 0

    @classmethod
    def get_instance(cls):
        lock.acquire()
        try:
            if not hasattr(cls, 'instance'):
                cls.instance = cls()
        finally:
            lock.release()
        return cls.instance

    def get(self, init_port):
        lock.acquire()
        try:
            port = int(init_port) + self._offset
            self._offset += 1
        finally:
            lock.release()
        return port
