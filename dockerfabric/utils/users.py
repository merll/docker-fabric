# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from fabric.api import sudo
from fabric.utils import error

from dockermap.shortcuts import addgroup, adduser, assignuser
from .output import single_line_stdout, check_int


def get_group_id(groupname):
    """
    Returns the group id to a given group name. Returns ``None`` if the group does not exist.

    :param groupname: Group name.
    :type groupname: unicode
    :return: Group id.
    :rtype: int
    """
    gid = single_line_stdout('id -g {0}'.format(groupname), expected_errors=(1,), shell=False)
    return check_int(gid)


def get_user_id(username):
    """
    Returns the user id to a given user name. Returns ``None`` if the user does not exist.

    :param username: User name.
    :type username: unicode
    :return: User id.
    :rtype: int
    """
    uid = single_line_stdout('id -u {0}'.format(username), expected_errors=(1,), shell=False)
    return check_int(uid)


def get_user_groups(username):
    """
    Returns the list if group names for a given user name, omitting the default group.
    Returns ``None`` if the user does not exist.

    :param username: User name.
    :type username: unicode
    :return: Group names.
    :rtype: list
    """
    out = single_line_stdout('groups {0}'.format(username))
    if out:
        return out.split()[2:]
    return None


def create_group(groupname, gid, system=True):
    """
    Creates a new user group with a specific id.

    :param groupname: Group name.
    :type groupname: unicode
    :param gid: Group id.
    :type gid: int or unicode
    :param system: Creates a system group.
    """
    sudo(addgroup(groupname, gid, system))


def create_user(username, uid, system=False, no_login=True, no_password=False, group=False, gecos=None):
    """
    Creates a new user with a specific id.

    :param username: User name.
    :type username: unicode
    :param uid: User id.
    :type uid: int or unicode
    :param system: Creates a system user.
    :type system: bool
    :param no_login: Disallow login of this user and group, and skip creating the home directory. Default is ``True``.
    :type no_login: bool
    :param no_password: Do not set a password for the new user.
    :type: no_password: bool
    :param group: Create a group with the same id.
    :type group: bool
    :param gecos: Provide GECOS info and suppress prompt.
    :type gecos: unicode
    """
    sudo(adduser(username, uid, system, no_login, no_password, group, gecos))


def assign_user_groups(username, groupnames):
    """
    Assigns a user to a set of groups. User and group need to exists. The new groups are appended to existing group
    assignments.

    :param username: User name.
    :type username: unicode
    :param groupnames: Group names.
    :type groupnames: iterable
    """
    sudo(assignuser(username, groupnames))


def get_or_create_group(groupname, gid_preset, system=False, id_dependent=True):
    """
    Returns the id for the given group, and creates it first in case it does not exist.

    :param groupname: Group name.
    :type groupname: unicode
    :param gid_preset: Group id to set if a new group is created.
    :type gid_preset: int or unicode
    :param system: Create a system group.
    :type system: bool
    :param id_dependent: If the group exists, but its id does not match `gid_preset`, an error is thrown.
    :type id_dependent: bool
    :return: Group id of the existing or new group.
    :rtype: int
    """
    gid = get_group_id(groupname)
    if gid is None:
        create_group(groupname, gid_preset, system)
        return gid_preset
    elif id_dependent and gid != gid_preset:
        error("Present group id '{0}' does not match the required id of the environment '{1}'.".format(gid, gid_preset))
    return gid


def get_or_create_user(username, uid_preset, groupnames=[], system=False, no_password=False, no_login=True,
                       gecos=None, id_dependent=True):
    """
    Returns the id of the given user name, and creates it first in case it does not exist. A default group is created
    as well.

    :param username: User name.
    :type username: unicode
    :param uid_preset: User id to set in case a new user is created.
    :type uid_preset: int or unicode
    :param groupnames: Additional names of groups to assign the user to. If the user exists, these will be appended to
      existing group assignments.
    :type groupnames: iterable
    :param system: Create a system user.
    :type system: bool
    :param no_login: Disallow login of this user and group, and skip creating the home directory. Default is ``True``.
    :type no_login: bool
    :param no_password: Do not set a password for the new user.
    :type: no_password: bool
    :param gecos: Provide GECOS info and suppress prompt.
    :type gecos: unicode
    :param id_dependent: If the user exists, but its id does not match `uid_preset`, an error is thrown.
    :type id_dependent: bool
    :return:
    """
    uid = get_user_id(username)
    gid = get_group_id(username)
    if id_dependent and gid is not None and gid != uid_preset:
        error("Present group id '{0}' does not match the required id of the environment '{1}'.".format(gid, uid_preset))
    if gid is None:
        create_group(username, uid_preset, system)
        gid = uid_preset
    if uid is None:
        create_user(username, gid, system, no_login, no_password, False, gecos)
        if groupnames:
            assign_user_groups(username, groupnames)
        return uid
    elif id_dependent and uid != uid_preset:
        error("Present user id '{0}' does not match the required id of the environment '{1}'.".format(uid, uid_preset))
    current_groups = get_user_groups(username)
    new_groups = set(groupnames).discard(tuple(current_groups))
    if new_groups:
        assign_user_groups(username, new_groups)
    return uid
