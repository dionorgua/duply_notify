"""
Created on Jun 6, 2016

License: GPLv2+

@author: dion
"""
import dbus
from dbus.exceptions import DBusException


class JobViewClient(object):
    CAN_CANCEL = 0x01
    CAN_SUSPEND = 0x02

    def __init__(self):
        self.id = None
        self.session_bus = dbus.SessionBus()
        self.job_iface = None

    def start(self, app_name, app_icon, capabilities):
        server = self.session_bus.get_object('org.kde.JobViewServer', '/JobViewServer')
        iface = dbus.Interface(server, 'org.kde.JobViewServer')
        res = iface.requestView(app_name, app_icon, capabilities)
        if res is None:
            raise ValueError('Unable to obtain job id')
        self.id = res

        job_object = self.session_bus.get_object('org.kde.JobViewServer', self.id)
        if job_object is None:
            raise ValueError('Unable to obtain job object')
        self.job_iface = dbus.Interface(job_object, 'org.kde.JobViewV2')

    def is_ready(self):
        return self.job_iface is not None

    def stop(self):
        try:
            self.terminate('')
        except DBusException:
            pass

        self.job_iface = None
        self.id = None

    def terminate(self, msg):
        self.job_iface.terminate(msg)

    def clear_description_field(self, number):
        return self.job_iface.clearDescriptionField(number)

    def set_description_field(self, number, name, value):
        return self.job_iface.setDescriptionField(number, name, value)

    def set_dest_url(self, dest_url):
        return self.job_iface.setDestUrl(dest_url)

    def set_error(self, error_code):
        return self.job_iface.setError(error_code)

    def set_info_message(self, message):
        return self.job_iface.setInfoMessage(message)

    def set_percent(self, percent):
        return self.job_iface.setPercent(percent)

    def set_processed_amount(self, amount, unit):
        return self.job_iface.setProcessedAmount(amount, unit)

    def set_speed(self, bytes_per_second):
        return self.job_iface.setSpeed(bytes_per_second)

    def set_suspended(self, suspended):
        return self.job_iface.setSuspended(suspended)

    def set_total_amount(self, amount, unit):
        return self.job_iface.setTotalAmount(amount, unit)
