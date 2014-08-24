# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from fabric.api import sudo

from dockermap.shortcuts import addgroup, adduser, assignuser
from .output import single_line_stdout, check_int


def get_group_id(groupname):
    gid = single_line_stdout('id -g {0}'.format(groupname), expected_errors=(1,), shell=False)
    return check_int(gid)


def get_user_id(username):
    uid = single_line_stdout('id -u {0}'.format(username), expected_errors=(1,), shell=False)
    return check_int(uid)


def get_user_groups(username):
    out = single_line_stdout('groups {0}'.format(username))
    return out.split()[2:]


def create_group(groupname, gid, system=True):
    sudo(addgroup(groupname, gid, system))


def create_user(username, uid, system=True, no_login=True):
    sudo(adduser(username, uid, system, no_login))


def assign_user_groups(username, groupnames):
    sudo(assignuser(username, groupnames))


def get_or_create_group(groupname, gid_preset, system=False, id_dependent=True):
    gid = get_group_id(groupname)
    if gid is None:
        create_group(groupname, gid_preset, system)
        return gid_preset
    elif id_dependent and gid != gid_preset:
        raise ValueError("Present group id '{0}' does not match the required id of the environment '{1}'.".format(gid, gid_preset))
    return gid


def get_or_create_user(username, uid_preset, groupnames=[], system=False, no_login=True, id_dependent=True):
    uid = get_user_id(username)
    gid = get_group_id(username)
    if gid is None:
        create_group(username, uid_preset, system)
    elif id_dependent and gid != uid_preset:
        raise ValueError("Present group id '{0}' does not match the required id of the environment '{1}'.".format(gid, uid_preset))
    if uid is None:
        create_user(username, uid_preset, system, no_login)
        if groupnames:
            assign_user_groups(username, groupnames)
        return uid
    elif id_dependent and uid != uid_preset:
        raise ValueError("Present user id '{0}' does not match the required id of the environment '{1}'.".format(uid, uid_preset))
    current_groups = get_user_groups(username)
    new_groups = set(groupnames).discard(tuple(current_groups))
    if new_groups:
        assign_user_groups(username, new_groups)
    return uid
