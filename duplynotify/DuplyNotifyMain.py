#!/usr/bin/python3
# encoding: utf-8
"""
duply_notify -- duplicity wrapper for KDE notification daemon

duply_notify is a duplicity wrapper that shows progress in KDE notification area

@author:     Dmitry Nezhevenko

@license:    GPLv2+

@contact:    dion@dion.org.ua
"""

import sys
import os

from argparse import ArgumentParser
from argparse import RawDescriptionHelpFormatter
from duplynotify.DuplyRunner import DuplyRunner
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

        parser.add_argument("-v", "--verbose", dest="verbose", action="store_true", help="set verbosity")
        parser.add_argument('-V', '--version', action='version', version=program_version_message)

        parser.add_argument('-n', '--name', action='store', default='duply',
                            help='application name for notification (default: duply)')
        parser.add_argument('-i', '--icon', action='store', default='ark', help='notification icon (default: ark)')

        # debug
        parser.add_argument('--debug-log', dest='debug_log', action='store', default=None,
                            help='save duplicity machine-readable log to file')
        parser.add_argument('--replay-log', dest='replay_log', action='store', default=None,
                            help='parse provided log file instead of running duplicity')
        parser.add_argument('--replay-speed', type=float, dest='replay_speed', action='store', default=1.0,
                            help='replay speed (2 will replay 2 times faster)')

        parser.add_argument('cmd', nargs='*', action='store', help='duplicity/duply command line')

        # Process arguments
        args = parser.parse_args()

        verbose = args.verbose

        if len(args.cmd) == 0 and not args.replay_log:
            parser.print_usage()
            return 1

        if verbose:
            print("Verbose mode on")
            globals.verbose = True

        globals.notification_app_name = args.name
        globals.notification_icon = args.icon
        globals.save_duply_log_file_name = args.debug_log
        globals.replay_log_file_name = args.replay_log
        globals.replay_log_speed = args.replay_speed

        return run_me(args.cmd)

    except KeyboardInterrupt:
        return 1
    except Exception as e:
        if DEBUG:
            raise
        indent = len(program_name) * " "
        sys.stderr.write(program_name + ": " + repr(e) + "\n")
        sys.stderr.write(indent + "  for help use --help")
        return 2


if __name__ == "__main__":
    if DEBUG:
        sys.argv.append("-v")
    sys.exit(main())
