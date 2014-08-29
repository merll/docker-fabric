# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from fabric import operations
from fabric.context_managers import hide
from fabric.utils import error


def stdout_result(cmd, expected_errors=(), shell=True, sudo=False, quiet=False):
    which = operations.sudo if sudo else operations.run
    with hide('warnings'):
        result = which(cmd, shell=shell, quiet=quiet, warn_only=True)
    if result.return_code == 0:
        return result

    if result.return_code not in expected_errors:
        error("Received unexpected error code {0} while executing!".format(result.return_code))
    return None


def check_int(value):
    if value is not None:
        try:
            return int(value)
        except TypeError:
            error("Unexpected non-integer value '{0}'.".format(value))
    return None


single_line = lambda val: val.split('\n')[0] if val is not None else None

single_line_stdout = lambda cmd, expected_errors=(), shell=True, sudo=False, quiet=False:\
    single_line(stdout_result(cmd, expected_errors, shell, sudo, quiet))
