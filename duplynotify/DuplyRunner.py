"""
Created on Jun 6, 2016

License: GPLv2+

@author: dion
"""
import subprocess
import re
import time
import os
from dbus.exceptions import DBusException

from duplynotify import globals
from duplynotify.JobViewClient import JobViewClient
from duplynotify.TimedReader import TimedReader


def print_sleep(msg):
    print('==> %s' % msg)


class DuplyRunner(object):
    def __init__(self, cmd_line, app_name, icon):
        self.cmd_line = cmd_line
        self.app_name = app_name
        self.icon = icon
        self.job = None
        self.debug_log_fd = None

        self.processed_handler = None

        self.backup_name = None
        self.estimate_done = False
        self.last_info_message = None
        self.last_volume_name = None
        self.last_status = None

        self.RE_PATTERNS = [
            (re.compile(r'Using backup name: (.*)$'), self.re_backup_name),
            ('Synchronizing remote metadata to local cache...', self.re_print_line),
            (re.compile(r'Copying (.*) to local cache.'), self.re_copy_to_local),
            ('Collection Status', self.re_handle_collection_status),
            # (re.compile('Reading globbing filelist: .*'), self.re_handle_globbing),
            (re.compile(r'Writing (.*\.gpg)$'), self.re_write_gpg),
            ('Create Par2 recovery files', self.re_par2),
        ]
        self.RE_HEAD_PATTERNS = [
            # changed_bytes, elapsed, progress, eta, speed, stalled)
            (re.compile(r'NOTICE 16 (?P<changed_bytes>\d+) (?P<elapsed>\d+) '
                        '(?P<progress>\d+) (?P<eta>\d+) (?P<speed>\d+) (?P<stalled>\d+)'),
             self.re_progress),
        ]

    def run(self):
        return self.run_internal(self.process)

    def run_fake(self, captured_logfile):
        self.processed_handler = print_sleep
        return self.run_internal(lambda: self.process_fake(captured_logfile))

    def run_internal(self, runner):
        self.check_setup_job()
        try:
            if globals.save_duply_log_file_name:
                self.debug_log_fd = open(globals.save_duply_log_file_name, 'w')
            res = runner()
        finally:
            if self.debug_log_fd:
                self.debug_log_fd.close()

        self.cleanup_job()
        return res

    def check_setup_job(self):
        try:
            if not self.job:
                self.job = JobViewClient()
            if not self.job.is_ready():
                self.job.start(self.app_name, self.icon, 0)

            if self.last_info_message:
                self.set_info_message(self.last_info_message)

            if self.last_status:
                self.set_status(self.last_status)

            if self.last_volume_name:
                self.set_volume_name(self.last_volume_name)

        except DBusException as e:
            print("DuplyRunner: %s" % e)

    def cleanup_job(self):
        self.job.set_info_message('')
        for idx in range(0, 2):
            self.job.clear_description_field(idx)

    def process(self):
        proc_obj = None
        log_read_fobj = None
        try:
            logfd_read, logfd_write = os.pipe()

            log_read_fobj = os.fdopen(logfd_read, 'r')
            os.set_inheritable(logfd_write, True)
            cmd = self.cmd_line[:]
            cmd.extend(['--log-fd', str(logfd_write)])

            proc_obj = subprocess.Popen(cmd, close_fds=False, stdin=subprocess.DEVNULL, shell=False)
            os.close(logfd_write)
            res = self.process_with_fd(proc_obj, log_read_fobj)
            return res
        except Exception as e:
            print("Backup failed!!!: %s" % e)
            self.job.terminate("Backup failed")
            raise
        finally:
            log_read_fobj.close()
            if proc_obj:
                proc_obj.kill()

    def process_fake(self, captured_logfile):
        fd = open(captured_logfile, 'r')
        try:
            fd = TimedReader(fd)
            # noinspection PyTypeChecker
            res = self.process_with_fd(None, fd)
            return res
        finally:
            fd.close()

    def process_with_fd(self, process_obj, log_fd):
        while True:
            line = log_fd.readline()
            if line == '' and (process_obj is None or process_obj.poll() is not None):
                break
            if line:
                line = line.strip()
                if self.debug_log_fd:
                    self.debug_log_fd.write('[%10.6f] %s\n' % (time.time(), line))
                if self.parse_line(line) and self.processed_handler:
                    self.processed_handler(line)

        if process_obj:
            rc = process_obj.poll()
        else:
            rc = 1
        return rc

    def parse_line(self, line):
        if line.startswith('. '):
            line = line[2:]
            patterns = self.RE_PATTERNS
        else:
            patterns = self.RE_HEAD_PATTERNS

        for regex, method in patterns:
            m = None
            if isinstance(regex, str):
                if regex == line:
                    m = line
            else:
                m = regex.match(line)
            if m:
                self.invoke_handler(method, m)
                return True
        return False

    def invoke_handler(self, method, match):
        try:
            self.check_setup_job()
            method(match)
        except DBusException as e:
            print("DuplyRunner: %s" % e)
            self.job.stop()

    @staticmethod
    def format_size(size_bytes):
        unit_list = ['KB', 'MB', 'GB']
        unit = 'B'
        size = size_bytes
        for new_unit in unit_list:
            if size > 1000:
                unit = new_unit
                size /= 1024
            else:
                break
        return size, unit

    def set_info_message(self, msg):
        self.last_info_message = msg
        self.job.set_info_message(msg)

    def set_status(self, msg):
        self.last_status = msg
        self.job.set_description_field(0, 'status', msg)

    def set_volume_name(self, volume_name):
        self.last_volume_name = volume_name
        self.job.set_description_field(1, 'volume', volume_name)

    def re_print_line(self, match):
        self.set_status(match)

    def re_backup_name(self, match):
        self.backup_name = match.group(1)
        self.set_info_message("duply: %s" % self.backup_name)

    def re_copy_to_local(self, match):
        vol = match.group(1)
        self.set_volume_name(vol)

    # noinspection PyUnusedLocal
    def re_handle_collection_status(self, match):
        self.set_volume_name('')
        self.set_status('Calculating changes')

    # noinspection PyUnusedLocal
    def re_handle_globbing(self, match):
        if not self.estimate_done:
            self.estimate_done = True
            self.set_status('starting backup')

    def re_write_gpg(self, match):
        vol_name = match.group(1)
        self.set_volume_name(vol_name)
        self.set_status("gpg: %s" % vol_name)

    # noinspection PyUnusedLocal
    def re_par2(self, match):
        self.set_status('par2: %s' % self.last_volume_name)

    def re_progress(self, match):
        # changed_bytes, elapsed, progress, eta, speed, stalled)
        changed_bytes = int(match.group('changed_bytes'))

        progress = int(match.group('progress'))
        speed = int(match.group('speed'))
        stalled = int(match.group('stalled'))
        if stalled:
            speed = 0

        changed_value, changed_unit = self.format_size(changed_bytes)
        self.set_status('uploading: %d %s' % (changed_value, changed_unit))

        self.job.set_percent(progress)
        self.job.set_speed(speed)
        self.job.set_processed_amount(changed_value, changed_unit)
