#!/usr/bin/python3
# encoding: utf-8
"""
duply_notify -- duplicity wrapper for KDE notification daemon

duply_notify is a duplicity wrapper that shows progress in KDE notification area

@author:     Dmitry Nezhevenko

@license:    GPLv2+

@contact:    dion@dion.org.ua
"""
import logging
import sys
import os

from argparse import ArgumentParser
from argparse import RawDescriptionHelpFormatter

from duplynotify.DBusEnv import dbus_update_environment
from duplynotify.DuplyRunner import DuplyRunner
from duplynotify.JobViewClient import JobViewClient
from duplynotify import globals

__all__ = []
__version__ = 0.1
__date__ = '2016-06-06'
__updated__ = '2016-06-06'

DEBUG = 0


class CLIError(Exception):
    """Generic exception to raise and log different fatal errors."""

    def __init__(self, msg):
        super(CLIError).__init__(type(self))
        self.msg = "E: %s" % msg

    def __str__(self):
        return self.msg

    def __unicode__(self):
        return self.msg


def test_dbus():
    dbus_update_environment()
    client = JobViewClient()
    msg = 'Press Enter to exit'
    client.start(globals.notification_app_name, globals.notification_icon, 0)
    client.set_info_message("duply_notify test")
    client.set_description_field(0, 'test', msg)
    print(msg)
    sys.stdin.readline()
    client.stop()


def run_me(cmd):
    runner = DuplyRunner(cmd, globals.notification_app_name, globals.notification_icon)
    if globals.replay_log_file_name:
        return runner.run_fake(globals.replay_log_file_name)
    return runner.run()


def main(argv=None):  # IGNORE:C0111
    """Command line options."""

    if argv is not None:
        sys.argv.extend(argv)

    program_name = os.path.basename(sys.argv[0])
    program_version = "v%s" % __version__
    program_build_date = str(__updated__)
    program_version_message = '%%(prog)s %s (%s)' % (program_version, program_build_date)
    program_shortdesc = __import__('__main__').__doc__.split("\n")[1]
    program_license = '''%s

  Created by Dmitry Nezhevenko on %s.
  Copyright 2016 Dmitry Nezhevenko. All rights reserved.

  Licensed under the GPLv2+

  Distributed on an "AS IS" basis without warranties
  or conditions of any kind, either express or implied.

USAGE
''' % (program_shortdesc, str(__date__))

    try:
        # Setup argument parser
        parser = ArgumentParser(description=program_license, formatter_class=RawDescriptionHelpFormatter)

        parser.add_argument('-V', '--version', action='version', version=program_version_message)

        # notification itself
        icon_opts = parser.add_argument_group('notification', 'notification look')

        icon_opts.add_argument('-t', '--title', action='store', default=None,
                               help='notification title (useful for duply with pre-backup script')
        icon_opts.add_argument('-n', '--name', action='store', default='duply',
                               help='application name for notification (default: duply)')
        icon_opts.add_argument('-i', '--icon', action='store', default='ark', help='notification icon (default: ark)')

        # dbus stuff
        dbus_opts = parser.add_argument_group('dbus', 'how to connect to DBus daemon')
        dbus_excl = dbus_opts.add_mutually_exclusive_group()
        dbus_excl.add_argument('--dbus-env', dest='dbus_env', action='store',
                               help='file to read dbus environment variables'
                                    ' (if current session has no DBUS_SESSION_BUS_ADDRESS).')
        dbus_excl.add_argument('--dbus-user', dest='dbus_user', action='store',
                               help='guess environment for user (from /home/$USER/.dbus/session-bus)')
        dbus_opts.add_argument('--dbus-test', '--test-dbus', dest='test_dbus', action='store_true',
                               help="just try to show notification without backup. Useful for dbus testing")

        # debug
        debug_opts = parser.add_argument_group('debug', 'debugging stuff')
        debug_opts.add_argument("-v", "--verbose", dest="verbose", action="store_true", help="set verbosity")

        debug_opts.add_argument('--debug-log', dest='debug_log', action='store', default=None,
                                help='save duplicity machine-readable log to file')
        debug_opts.add_argument('--replay-log', dest='replay_log', action='store', default=None,
                                help='parse provided log file instead of running duplicity')
        debug_opts.add_argument('--replay-speed', type=float, dest='replay_speed', action='store', default=1.0,
                                help='replay speed (2 will replay 2 times faster)')

        parser.add_argument('cmd', nargs='*', action='store', help='duplicity/duply command line')

        # Process arguments
        args = parser.parse_args()

        verbose = args.verbose

        if len(args.cmd) == 0 and not args.replay_log and not args.test_dbus:
            parser.print_usage()
            return 1

        if verbose:
            print("Verbose mode on")
            globals.verbose = True
            logging.basicConfig(level=logging.DEBUG)

        globals.notification_title = args.title
        globals.notification_app_name = args.name
        globals.notification_icon = args.icon

        globals.dbus_user = args.dbus_user
        globals.dbus_env = args.dbus_env

        globals.save_duply_log_file_name = args.debug_log
        globals.replay_log_file_name = args.replay_log
        globals.replay_log_speed = args.replay_speed

        if args.test_dbus:
            return test_dbus()

        return run_me(args.cmd)

    except KeyboardInterrupt:
        return 1
    except Exception as e:
        if DEBUG or globals.verbose:
            raise
        indent = len(program_name) * " "
        sys.stderr.write(program_name + ": " + repr(e) + "\n")
        sys.stderr.write(indent + "  for help use --help")
        return 2


if __name__ == "__main__":
    if DEBUG:
        sys.argv.append("-v")
    sys.exit(main())
