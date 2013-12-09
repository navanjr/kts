
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
        basePath = os.path.dirname(os.path.realpath(__file__))
        m = ktsMenu(basePath=basePath)
        s = kirc(menu=m)
        m.setIRC(s)
        m.log('starting right now...')

        noticeIRC = True if m.settings['noticeEnabled'] == 'TRUE' else False

        if noticeIRC:
            noticeEventLoop = True if m.settings['noticeEventLoop'] == 'TRUE' else False
            s.connect(room='#kts_notice', nickname=m.settings['noticeName'])
            if noticeEventLoop:
                m.apiServiceControl(enableService=True)

        cont, restart, restartSeconds = True, True, 5

        bt = stopWatch()

        while True:
            rc = win32event.WaitForSingleObject(self.hWaitStop, self.timeout)
            if rc == win32event.WAIT_OBJECT_0:
                # Stop signal encountered
                restart = False
                break

            if noticeIRC:
                try:
                    cont, restart = s.listen()
                except Exception as e:
                    # if there is any exceptions i will die and restart in 60 seconds
                    m.log('problem while listing for irc traffic... %s' % e)
                    restartSeconds = 60
                    restart = True
                    break

            # backup routine - only runs every 5 minutes
            if bt.elaps() > 300:
                if m.doWeNeedToRunTheBackUp():
                    m.log('I think we need to run the backup...')
                    backupResult = m.backupSQLData()
                    m.log('I just ran a SQL backup and here is the result...%s' % backupResult)
                    if noticeIRC:
                        s.psend('I just ran a SQL backup and here is the result...%s' % backupResult)
                bt.reset()

            if not cont:
                break

        m.log('shutting down...')
        if restart:
            m.log('... however, i will restart in %s seconds' % restartSeconds)
            subprocess.Popen('sleep %s & sc start %s' % (restartSeconds, self._svc_name_), shell=True)

if __name__ == '__main__':
    win32serviceutil.HandleCommandLine(AppServerSvc)

