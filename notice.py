
__author__ = 'nate'
from kirc import *
import pythoncom
import win32serviceutil
import win32service
import win32event
import servicemanager
import socket
import os
import subprocess
from functions import *

class AppServerSvc (win32serviceutil.ServiceFramework):
    _svc_name_ = "aaa_kellpro_notice"
    _svc_display_name_ = "aaa kellpro notice service"

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        # socket.setdefaulttimeout(60)

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.hWaitStop)

    def SvcDoRun(self):
        servicemanager.LogMsg(servicemanager.EVENTLOG_INFORMATION_TYPE,
                              servicemanager.PYS_SERVICE_STARTED,
                              (self._svc_name_, ''))

        self.timeout = 1000
        self.main()

    def main(self):
        log('starting right now...')
        basePath = os.path.dirname(os.path.realpath(__file__))
        m = ktsMenu(basePath=basePath)
        s = kirc(menu=m)
        s.connect(room='#kts_notice', nickname=m.settings['noticeName'])

        cont, restart = True, True

        while True:
            rc = win32event.WaitForSingleObject(self.hWaitStop, self.timeout)
            if rc == win32event.WAIT_OBJECT_0:
                # Stop signal encountered
                restart = False
                break

            cont, restart = s.listen()
            if not cont:
                break

        if restart:
            subprocess.Popen('sleep 5 & sc start %s' % self._svc_name_, shell=True)

if __name__ == '__main__':
    win32serviceutil.HandleCommandLine(AppServerSvc)

