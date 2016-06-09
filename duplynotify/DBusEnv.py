#!/usr/bin/python3
"""
duply_notify -- duplicity wrapper for KDE notification daemon

duply_notify is a duplicity wrapper that shows progress in KDE notification area

@author:     Dmitry Nezhevenko

@license:    GPLv2+

@contact:    dion@dion.org.ua
"""
import logging
import os

from duplynotify import globals

log = logging.getLogger(__name__)


def dbus_update_environment():
    if globals.dbus_env:
        return dbus_read_env_file(globals.dbus_env)

    if globals.dbus_user:
        return dbus_read_user(globals.dbus_user)


def dbus_read_user(user_name):
    machine_id_file = '/etc/machine-id'
    with open(machine_id_file, 'r') as f:
        machine_id = f.readline().strip()

    log.debug('Machine id: %s (from %s)' % (machine_id, machine_id_file))

    home_dir = os.path.expanduser('~'+user_name)
    session_path = os.path.join(home_dir, '.dbus', 'session-bus')

    log.debug('Finding session files in %s' % session_path)

    session_files = [os.path.join(session_path, fn) for fn in os.listdir(session_path) if fn.startswith(machine_id)]
    session_files = sorted(session_files, key=lambda x: -os.stat(x).st_mtime)

    log.debug('Possible session files (sorted): %s' % session_files)

    if len(session_files) == 0:
        raise ValueError('no session files found: %s' % session_path)

    dbus_read_env_file(session_files[0])


def dbus_read_env_file(file_name):
    log.debug('Reading session file: %s' % file_name)
    expected_var = 'DBUS_SESSION_BUS_ADDRESS'
    value = None
    with open(file_name, 'r') as f:
        for x in f.readlines():
            if x.startswith(expected_var):
                kv_list = x.strip().split('=')
                value = '='.join(kv_list[1:])
    if not value:
        log.error("Can't find %s in file %s" % (expected_var, file_name))
        return
    log.debug('setting %s=%s' % (expected_var, value))
    os.environ[expected_var] = value
