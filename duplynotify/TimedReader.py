"""
Created on Jun 6, 2016

License: GPLv2+

@author: dion
"""

import re
import time

from duplynotify import globals

TIMESTAMP_RE = re.compile(r'^\[([\d\.]+)\] (.*)$')


class TimedReader(object):

    def __init__(self, f_obj):
        self.f_obj = f_obj
        self.prev_time = None

    def readline(self):
        res = self.f_obj.readline()
        if res is None:
            return res

        m = TIMESTAMP_RE.match(res)
        if not m:
            return res

        msg_time = float(m.group(1))
        res = m.group(2)

        # sleep a bit if needed
        if self.prev_time is not None:
            delta = msg_time - self.prev_time
            sleep_time = delta / globals.replay_log_speed
            if sleep_time > 1 or sleep_time < 0:
                sleep_time = 1.0
            time.sleep(sleep_time)

        self.prev_time = msg_time

        if res == "":
            return " "
        return res

    def close(self):
        self.f_obj.close()
