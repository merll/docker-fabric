# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from invoke import Exit


def stdout_result(c, cmd, expected_errors=(), shell=True, sudo=False, quiet=False):
    """
    Runs a command and returns the result, that would be written to `stdout`, as a string. The output itself can
    be suppressed.

    :param c: Fabric connection.
    :type c: fabric.connection.Connection
    :param cmd: Command to run.
    :type cmd: unicode | str
    :param expected_errors: If the return code is non-zero, but found in this tuple, it will be ignored. ``None`` is
      returned in this case.
    :type expected_errors: tuple
    :param shell: Use a shell.
    :type shell: bool
    :param sudo: Use `sudo`.
    :type sudo: bool
    :param quiet: If set to ``True``, does not show any output.
    :type quiet: bool
    :return: The result of the command as would be written to `stdout`.
    :rtype: unicode | str
    """
    which = c.sudo if sudo else c.run
    if quiet:
        hide = 'stdout'
    else:
        hide = None
    result = which(cmd, shell=shell, warn=True, hide=hide)
    if result.return_code == 0:
        return result.stdout

    if result.return_code not in expected_errors:
        raise Exit("Received unexpected error code {0} while executing!".format(result.return_code))
    return None


def check_int(value):
    """
    Tests a given string for a possible conversion to integer. Uses Fabric's :func:`fabric.utils.error` instead of
    raising a :class:`TypeError`. ``None`` is not converted but returns ``None`` instead.

    :param value: Value to test for conversion.
    :type value: unicode | str
    :return: Integer value.
    :rtype: int
    """
    if value is not None:
        try:
            return int(value)
        except TypeError:
            raise Exit("Unexpected non-integer value '{0}'.".format(value))
    return None


single_line = lambda val: val.split('\n')[0] if val is not None else None


def single_line_stdout(c, cmd, expected_errors=(), shell=True, sudo=False, quiet=False):
    """
    Runs a command and returns the first line of the result, that would be written to `stdout`, as a string.
    The output itself can be suppressed.

    :param c: Fabric connection.
    :type c: fabric.connection.Connection
    :param cmd: Command to run.
    :type cmd: unicode | str
    :param expected_errors: If the return code is non-zero, but found in this tuple, it will be ignored. ``None`` is
      returned in this case.
    :type expected_errors: tuple
    :param shell: Use a shell.
    :type shell: bool
    :param sudo: Use `sudo`.
    :type sudo: bool
    :param quiet: If set to ``True``, does not show any output.
    :type quiet: bool
    :return: The result of the command as would be written to `stdout`.
    :rtype: unicode | str
    """
    return single_line(stdout_result(c, cmd, expected_errors, shell, sudo, quiet))
