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
        self.backup_main_action = None
        self.is_estimate_done = False
        self.last_info_message = None
        self.last_file_name = None
        self.last_file_name_rate_dict = {}
        self.last_volume_name = None
        self.last_status = None
        self.is_uploading = False
        self.is_adding_files = False

        self.RE_PATTERNS = [
            (re.compile(r'Using backup name: (.*)$'), self.re_backup_name),
            (re.compile(r'Main action: (.*)$'), self.re_main_action),
            ('Synchronizing remote metadata to local cache...', self.re_print_line),
            (re.compile(r'Copying (.*) to local cache.'), self.re_copy_to_local),
            ('Collection Status', self.re_handle_collection_status),
            (re.compile(r'AsyncScheduler: instantiating at concurrency.*$'), self.re_handle_startup),
            (re.compile(r'Writing (.*\.gpg)$'), self.re_write_gpg),
            ('Create Par2 recovery files', self.re_par2),
        ]
        self.RE_HEAD_PATTERNS = [
            # changed_bytes, elapsed, progress, eta, speed, stalled)
            (re.compile(r'NOTICE 16 (?P<changed_bytes>\d+) (?P<elapsed>\d+) '
                        '(?P<progress>\d+) (?P<eta>\d+) (?P<speed>\d+) (?P<stalled>\d+)'),
             self.re_progress),
            (re.compile(r'INFO (4|5|6) \'(?P<file_name>.*)\''), self.re_diff_file),
            (re.compile(r'INFO (11|12)'), self.re_upload_begin),
            (re.compile(r'INFO (13|14)'), self.re_upload_done),
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
                else:
                    self.update_info_message()

                if self.last_status:
                    self.set_status(self.last_status)

                if self.last_file_name:
                    self.set_file_name(self.last_file_name)

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
        except KeyboardInterrupt:
            print("Keyboard interrupt!!!")
            self.cleanup_job()
            raise
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

                if globals.verbose:
                    print(line)

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

    def update_info_message(self):
        res = globals.notification_title
        if res is None and self.backup_name is not None:
            res = self.backup_name
        if res is None:
            res = 'backup'
        if self.backup_main_action is not None:
            res += " (%s)" % self.backup_main_action
        self.set_info_message(res)

    def set_status(self, msg):
        self.last_status = msg
        self.job.set_description_field(0, 'status', msg)

    def set_file_name(self, file_name, rate_limit_key=None):
        self.last_file_name = file_name

        if rate_limit_key is not None:
            prev_time = self.last_file_name_rate_dict.get(rate_limit_key, 0)
            new_time = time.time()
            if new_time - prev_time < 2.0:
                return

            self.last_file_name_rate_dict[rate_limit_key] = new_time

        self.job.set_description_field(1, 'file', file_name)

    def re_print_line(self, match):
        self.set_status(match)

    def re_backup_name(self, match):
        self.backup_name = match.group(1)
        self.update_info_message()

    def re_main_action(self, match):
        self.backup_main_action = match.group(1)
        self.update_info_message()

    def re_copy_to_local(self, match):
        vol = match.group(1)
        self.set_file_name(vol)

    # noinspection PyUnusedLocal
    def re_handle_collection_status(self, match):
        self.set_file_name('')
        self.set_status('Calculating changes')

    def re_handle_startup(self, _):
        if not self.is_estimate_done:
            self.is_estimate_done = True
            self.is_adding_files = False
            self.set_status('Backup in progress')
            time.sleep(10)

    def mark_estimate_done(self):
        self.is_uploading = False
        self.is_estimate_done = True

    def re_write_gpg(self, match):
        self.mark_estimate_done()
        self.is_adding_files = False
        self.last_volume_name = match.group(1)
        self.set_file_name(self.last_volume_name)
        self.set_status("gpg: %s" % self.last_volume_name)

    # noinspection PyUnusedLocal
    def re_par2(self, match):
        self.mark_estimate_done()
        self.is_adding_files = False
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

        if self.is_uploading:
            self.set_status('uploading: %d %s' % (changed_value, changed_unit))

        self.job.set_percent(progress)
        self.job.set_speed(speed)
        self.job.set_processed_amount(changed_value, changed_unit)

    def re_diff_file(self, match):
        file_name = match.group('file_name')
        self.set_file_name(file_name, rate_limit_key='diff_file')
        if not self.is_adding_files:
            self.is_adding_files = True
            if self.is_estimate_done:
                self.set_status("scanning/adding files")

    def re_upload_begin(self, _):
        self.mark_estimate_done()
        self.is_uploading = True
        self.is_adding_files = False

    def re_upload_done(self, _):
        self.is_uploading = False
