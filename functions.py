import os
import sys
import pyodbc
import ConfigParser
import ftplib
import shutil
import kpsFunctions
from general import *
import importDBF
import threading
import time
# from kirc import *


class ktsMenu():
    def __init__(self, database=None, basePath=None):
        self.settings = {}
        self.ftpSettings = {}
        self.basePath = basePath
        if self.basePath:
            self.defaultFileName = "%s\\..\\ktsConfig.ini" % self.basePath
        else:
            self.defaultFileName = "..\\ktsConfig.ini"
        if database:
            self.dbSettings(database)
        else:
            self.dbSettings(self.configStuff('importDefaults', 'database') or 'kts')

        self.settings['server'] = self.configStuff('importDefaults', 'server') or '.'
        self.settings['uid'] = self.configStuff('importDefaults', 'uid')
        self.settings['password'] = self.configStuff('importDefaults', 'password')

        self.settings['noticeName'] = self.settingsF('site.noticeName', 'Unknown')

        self.tasks = tasks(self.settings['database'])
        self.ftpSettingsInit()
        self.apiLoopingResource = None

        self.apiSettingsKps = {
            'host': self.settingsF('site.apiurl'),
            'key': self.settingsF('site.apikey'),
            'siteId': self.settingsF('site.apisitecode'),
            'origin': 'kpsMike',
        }

        self.kpsTaxroll = kpsFunctions.kps(self, apiSettings=self.apiSettingsKps, pathToDBFs=self.settingsF('conversion.mikepathtax'), countyName=self.settings['database'])

        self.conversionSettings = [
            'conversion.mikepath',
            'conversion.mikepathtax',
            'conversion.officialbankcode',
            'conversion.initials',
            'conversion.conversiondate',
            'conversion.cutoffdate',
            'conversion.taxyear',
        ]

        self.commands = {}
        self.createCommand('exit',['x','exit','q','quit'],'exit ktsMenu',self.command_exit)
        self.createCommand('help',['h','help'],'',self.command_help, chatFunction=self.chat_help)
        self.createCommand('testConnection',['test','t','testconnection'],'tests the connection to your sql server',self.command_testConnection)
        self.createCommand('serverSettings',['set'],'modify server settings',self.command_serverSettings)
        self.createCommand('displayMenu',['m','menu','display','displayMenu','refresh'],'redraw menu',self.command_displayMenu,chatFunction=self.chat_displayMenu)
        self.createCommand('gitCommands',['git'],'run git command',self.command_git)
        self.createCommand('logging',['logging','log','logit'],'modify log settings',self.command_logging)
        self.createCommand('import',['i','import'],'import from repo into your database',self.command_import)
        self.createCommand('diagSQLObjects',['diagsql','diagsqlobjects'],'runs sqlObjects diagnostic',self.diag_sqlObjects)
        self.createCommand('setup',['setup'],'access all the setup options',self.command_initialSetup)
        self.createCommand('importSQLObject',['importsqlobject','importsql'],'import a named sql object from the repo',self.command_importSqlObject)
        self.createCommand('diagnostics',['d','diag','diagnostic','diagnostics'],'access all diagnostic options',self.command_diagnostics)
        self.createCommand('conversion',['c','conv','conversion'],'access all the conversion tools',[self.command_diagnostics,'conversion'])
        self.createCommand('restore',['restore'],'restore sql data to existing db',self.command_restore)
        self.createCommand('backup',['backup','back'],'back up sql data',self.command_backup)
        self.createCommand('backupNow',['backupNow',],'back up sql data without an "are you sure" prompt',self.command_backupNow)
        self.createCommand('users',['user','users'],'display or define default users',self.command_users)
        self.createCommand('gitstatus',['gitstatus','status','s'],'preform a git status',[self.command_git,['git','status']])
        self.createCommand('gitpull',['pull','p'],'preform a git log',[self.command_git,['git','pull']])
        self.createCommand('gitpush',['push'],'preform a git push ',self.command_gitpush)
        self.createCommand('ftp',['ftp'],'put a file to the support server',self.ftp_show)
        self.createCommand('gitstatusporcelain',['gsp'],'preform a porcelain git status',self.command_importSpecial)
        self.createCommand('devup',['devup','devon'],'set all developer defaults on your database',self.command_devup)
        self.createCommand('kps',['kps'],'kps upload to API',self.kpsTaxroll.menu)
        self.createCommand('nateTest',['nate'],'test menu option',self.nateTest)
        self.createCommand('checkoutTag',['checkout'],'fetch and checkout tag',self.command_gitCheckout, chatFunction=self.chat_gitCheckout)

        self.createCommand('api',['api', ],'run api job',self.command_api, chatFunction=self.chat_api)
        self.createCommand('apiSite',['site', ],'return site info from the api',self.command_apiSite, 'api')
        self.createCommand('apiSettings',['settings','set' ],'return api settings',self.command_apiSettings, 'api')
        self.createCommand('apiResourceControl',['resource','res' ],'toggle api service (api res X)',self.command_apiResourceControl, 'api')
        self.createCommand('apiLooper',['loop','looper' ],'fire up the api looper (api loop X)',self.command_apiLooper, 'api')
        self.createCommand('apiReset',['reset', ],'reset all the rows for resource (api reset X)',self.command_apiReset, 'api')
        self.createCommand('apiService',['service', 'serv'],'start the api Service Event Loop',self.command_apiService, 'api')

        self.createCommand('schtasks',['tasks', 'task'],'display all kts tasks',self.cp)
        self.createCommand('auto',['auto','a'],'setup all needed schedules',self.tasks.auto,'schtasks')
        self.createCommand('delete',['delete','del','d'],'delete a scheduled task',self.tasks.delete,'schtasks')
        self.createCommand('run',['run','r'],'run a scheduled task now',self.tasks.runTask,'schtasks')

        self.createCommand('settings',['set','settings'],'show all ftp settings',self.ftp_settings,'ftp')
        self.createCommand('put',['put'],'put a file to support',self.ftp_put,'ftp')

        self.createCommand('battery',['b','bat','batt','battery'],'runs light diagnostic battery',self.diagnostic_run,'diagnostics')
        self.createCommand('fix',['f','fix'],'runs diagnostic fix routine, requires the specific diagnostic number',self.diagnostic_fix,'diagnostics')

        self.createCommand('battery',['b','bat','batt','battery'],'runs conversion diagnostic battery',[self.diagnostic_run,'conversion'],'conversion')
        self.createCommand('settings',['settings'],'displays all conversion settings',self.diagnostic_conversionSettings,'conversion')
        self.createCommand('fix',['f','fix'],'runs conversion fix routine requires the specific diagnostic number',[self.diagnostic_fix,'conversion'],'conversion')
        self.createCommand('auto', ['a', 'auto'], 'runs a collection of conversion fix routines', self.diagnostic_auto, 'conversion')
        self.createCommand('aamasterCheck', ['aamasterCheck', ], 'copies some aamaster data into aamasterCheck for kts reports', self.tpsAamasterCheck, 'conversion')
        self.createCommand('aamasterUpdate', ['aamasterUpdate', ], 'update adtax with data from aamaster', self.tpsAamasterUpdate, 'conversion')
        self.createCommand('aamasterKey', ['aamasterKey', ], 'print data from aamaster', self.tpsAamasterKey, 'conversion')
        self.createCommand('importTax', ['importTax', ], 'copies XXXXadtax data into kts for invoicing', self.tpsXXXXadtax, 'conversion')
        self.createCommand('importGSI', ['importGSI', ], 'copies GSI data into aamasterCheck', self.gsiAamasterCheck, 'conversion')
        self.createCommand('importGSITax', ['importGSITax', ], 'copies TaxRoll data into kts for invoicing', self.gsiTaxroll, 'conversion')
        self.createCommand('importDBF', ['importDBF', ], 'copies any dbf into a sql table temp_?', self.importDBF, 'conversion')

        self.command = []

        self.git = {}
        self.gitVars()

        self.apiService = {
            'running': False,
            'eventRunning': False,
            'odometer': 0
        }

        self.chatObj = {}

    def nateTest(self):
        print self.chatKeywords()

    def chatCommands(self):
        cmds = []
        for key, value in self.commands.items():
            if value['chatFunction']:
                cmds.append(key)
        return cmds

    def chatKeywords(self):
        keywords = []
        for key in self.chatCommands():
            keywords += [keyword for keyword in self.commands[key]['keywords'] if len(keyword) > 1]
        return keywords

    def chatCommandFromKeyword(self, keyword):
        for key in self.chatCommands():
            if keyword in self.commands[key]['keywords']:
                return key

    def chatCommand(self, keyword, chatObj=None):
        self.chatObj = chatObj
        self.chatObj['cmd'] = self.chatObj['chatString'].split()
        cmd = self.chatCommandFromKeyword(keyword)
        if cmd:
            return self.commands[cmd]['chatFunction']()

    def threadit(self, name, targetProc):
        t = threading.Thread(name=name, target=targetProc)
        t.setDaemon(True)
        t.start()

    def importDBF(self):
        if len(self.command) == 3:
            tableName = self.command[2]
            foxFile = self.settingsF('conversion.%s' % tableName, None)
            if foxFile:
                fox = importDBF.dbfClass(foxFile, tableName)
                fox.load()
                data = fox.get()
                print 'Drop and create %s...' % data['tableName'], self.sqlQuery(data['dropAndCreateTableSQL'], True)['code']
                for row in data['insertRows']:
                    self.sqlQuery(row, True)

    def command_devup(self):
        self.sendCommand('set gitpath')
        self.sendCommand('set gitcommitter TRUE')
        self.sendCommand('log on')

    def apiStatus(self):
        rows = self.sqlQuery("select abs(id),resource,total,stale,jobEnabled,batchSize,rate,loopProcSpid,ageMinutes,lastLog from dbo.apiControlBRW()")['rows']
        obj = {}
        for row in rows:
            obj[row[0]] = {
                'resource': row[1],
                'total': row[2],
                'stale': row[3],
                'jobEnabled': row[4],
                'batchSize': row[5],
                'rate': row[6],
                'loopProcSpid': row[7],
                'ageMinutes': row[8],
                'lastLog': row[9],
            }
        return obj

    def chat_api(self):
        def getApiStatus():
            apiStatus = [self.apiService]
            for key, value in self.apiStatus().items():
                if value['jobEnabled'] == 1:
                    apiStatus.append({
                        value['resource']: {
                            'stale': value['stale'],
                            'batchSize': value['batchSize'],
                            'ageMinutes': value['ageMinutes'],
                            # 'jobEnabled': value['jobEnabled'],
                        }
                    })
            return apiStatus

        cmd = self.chatObj['chatString'].split()
        if len(cmd) == 1:
            return getApiStatus()
        elif cmd[1] in ('serv', 'service'):
            if len(cmd) == 3:
                if cmd[2] == 'on':
                    self.apiServiceControl(enableService=True)
                    return [self.apiService]
                elif cmd[2] == 'off':
                    self.apiServiceControl(enableService=False)
                    return [self.apiService]
            else:
                return 'huh?... im expecting "api service on" or "api service off"'
        elif cmd[1] in ('toggle', 'tog'):
            if len(cmd) == 3:
                self.apiResourceToggle(cmd[2])
                return getApiStatus()
        else:
            return 'huh?... '

    def apiShow(self, data):
        print
        print "        Api Service: %s" % self.apiService
        print
        print "      %s %s %s %s %s %s %s %s" % ('Resource'.ljust(15), '   Total', '   Stale', 'Status', 'Size', '    Rate', 'ageMin', 'log')
        print "      %s" % ("-" * 72)
        for key, value in data.items():
            status = 'on' if value['jobEnabled'] == 1 else 'off'
            status = 'looper' if value['loopProcSpid'] else status
            print "   %s %s %s %s %s %s %s %s %s" % (
                str(key).ljust(2),
                value['resource'].ljust(15),
                str(value['total']).rjust(8),
                str(value['stale']).rjust(8),
                status.rjust(6),
                str(value['batchSize']).rjust(4),
                str(value['rate']).rjust(8),
                str(value['ageMinutes']).rjust(6),
                str(value['lastLog']),
            )

    def command_api(self):
        cmd = self.command
        menuName = self.getMenuName(cmd[0], self.commands)
        subMenu = self.commands[menuName]['subMenu']
        apiRows = self.apiStatus()
        if len(cmd) < 2:
            self.apiShow(apiRows)
        if len(cmd) == 1:
            self.menuShow(subMenu)
        elif len(cmd) > 1:
            self.runMenuFunction(cmd[1], subMenu)
        if len(cmd) == 2 and cmd[1] in [value['resource'] for key, value in apiRows.items()]:
            print "exec api job...", self.sqlQuery("exec dbo.%s @method='job', @dropRawFile='TRUE'" % self.command[1])['code']

    def apiServiceControl(self, enableService=False):
        s = self.apiService
        if enableService:
            self.threadit('apiService', self.bulletProofApiServiceEventLoop)
        else:
            s['running'] = False

    def command_apiService(self):
        s = self.apiService
        print 'api Service running: %s (%s)' % (s['running'], s['odometer'])
        if s['running']:
            if areYouSure('do you want to turn this service off?'):
                self.apiServiceControl(enableService=False)
        else:
            if areYouSure('do you want to turn this service on?'):
                self.apiServiceControl(enableService=True)

    def bulletProofApiServiceEventLoop(self):
        s = self.apiService
        # bail if service is already running
        if s['running']:
            return

        s['running'] = True

        while True:
            if not s['running']:
                break

            try:
                self.apiServiceEvent()
            except:
                s['eventRunning'] = False

        # turn the lights off when going out the door
        s['running'] = False

    def apiServiceEvent(self):
        s = self.apiService
        # bail if event is already running
        if s['eventRunning']:
            return
        # test when raising exception
        # if s['odometer'] == 3:
        #     raise Exception('test')

        s['eventRunning'] = True

        qOutput = self.sqlQuery("select top 1 resource from dbo.apiControlBRW() where jobEnabled = 1 and stale > 0 order by lastTime")
        if qOutput['rows']:
            print 'here is what i found [rows]: %s' % qOutput['rows']
            resource = qOutput['rows'][0][0]
            self.sqlQuery("dbo.api%s @method='JOB'" % resource)
            s['odometer'] += 1
        else:
            time.sleep(int(dbo.settingF('api.sleepSeconds', '300')))
        # turn the lights off when going out the door
        s['eventRunning'] = False

    def apiResourceToggle(self, resource, verbose=True):
        resources = [value['resource'].lower() for key, value in self.apiStatus().items()]
        if resource.lower() in resources:
            qOutput = self.sqlQuery("exec dbo.apiJobs '%s', @method='toggle'" % resource, True)['code']
            if verbose:
                print "toggling %s resource..." % resource, qOutput

    def command_apiResourceControl(self):
        cmd = self.command
        apiRows = self.apiStatus()
        if len(cmd) == 2:
            if areYouSure('Are you sure you want to toggle all resources?'):
                for key, value in apiRows.items():
                    self.apiResourceToggle(value['resource'])
        elif len(cmd) == 3:
            self.apiResourceToggle(apiRows[int(cmd[2])]['resource'])

    def command_apiReset(self):
        cmd = self.command[1:]
        if len(cmd) == 2:
            try:
                opt = int(cmd[1])
            except ValueError:
                return
            apiRows = self.apiStatus()
            if opt in apiRows:
                resource = apiRows[opt]['resource']
                if areYouSure('are you sure you wish to reset all the row in resource: %s' % resource):
                    print "Reseting api %s" % resource, self.sqlQuery("exec dbo.apiControl '%s', @method='reset'" % resource, True)['code']

    def command_apiLooper(self):
        cmd = self.command[1:]
        if len(cmd) == 2:
            if cmd[1] in ['stop', 'off']:
                self.command_setSetting('api', settingName='looperEnabled', newValue='FALSE')
                return
            try:
                opt = int(cmd[1])
            except ValueError:
                return
            apiRows = self.apiStatus()
            if opt in apiRows:
                if areYouSure('are you sure you wish to start a looping thread'):
                    self.command_setSetting('api',settingName='looperEnabled', newValue='TRUE')
                    self.apiLoopingResource = apiRows[opt]['resource']
                    self.threadit('api.%s' % self.apiLoopingResource, self.apiLoop)

    def apiLoop(self):
        resource = self.apiLoopingResource
        appName = "kts.bat.api.%s" % resource
        print "starting %s looper..." % resource, self.sqlQuery("exec dbo.apiLooper '%s'" % resource, True, appName=appName)['code']

    def command_apiSettings(self):
        settings = ['site.apiurl', 'site.apikey', 'site.apisitecode']
        print
        for setting in settings:
            print "        %s %s" % (setting, self.settingsF(setting))

    def command_apiSite(self):
        host = self.apiSettingsKps['host']
        apiKey = self.apiSettingsKps['key']
        sites = apiCall(host, apiKey)
        for site in sites:
            print site

    def gitModified(self, repoDir=os.path.dirname(os.path.realpath(__file__))):
        p = subprocess.check_output('git status --porcelain', shell=True).split('\n')
        out = []
        for id, row in enumerate(p):
            if len(row.lstrip().split(' ')) > 1:
                d = {}
                d['raw'] = row.lstrip().split(' ')
                d['gitType'] = d['raw'][0]
                if '/' in d['raw'][1]:
                    d['sourceFolder'] = d['raw'][1].split('/')[0]
                    d['fileName'] = d['raw'][1].split('/')[1]
                else:
                    d['sourceFolder'] = ''
                    d['fileName'] = d['raw'][1]
                if '~' in d['fileName']:
                    d['name'] = d['fileName'].split('~')[0]
                    if d['sourceFolder'] == 'SqlObjects':
                        d['objectType'] = d['fileName'].split('~')[1]
                        d['objectNumber'] = d['fileName'].split('~')[2].replace('.TXT','')
                    else:
                        d['objectType'] = ''
                        d['objectNumber'] = ''
                else:
                    d['name'] = d['fileName'].replace('.TXT','')
                    d['objectType'] = ''
                    d['objectNumber'] = ''
                out.append(d)
        return out

    def command_importSpecial(self):
        modified = self.gitModified()
        if len(self.command) == 2:
            num = int(self.command[1]) - 1
            file = modified[num]
            print '%s...' % file['name'], file['name'], file['objectType'], file['objectNumber']
            if file['sourceFolder'] == 'SqlObjects':
                print 'running import... %s' % file['name'], self.sqlQuery('exec dbo.keySQLObjectUpdateFromRepo %s' % file['name'], True)['code']
                print 'running dispatcher... %s' % file['name'], self.sqlQuery("exec dbo.keySQLObjectDispatcher null, @name = '%s'" % file['name'], True)['code']
        else:
            for id, file in enumerate(modified):
                print '%-*s %-*s %-*s %-*s %s' % (3,id + 1, 4,file['gitType'], 15, file['sourceFolder'], 20, file['name'], file['objectType'])

    def ftpSettingsInit(self):
        self.ftpSettings['host'] = self.configStuff('ftp', 'host')
        self.ftpSettings['user'] = self.configStuff('ftp', 'user')
        self.ftpSettings['password'] = self.configStuff('ftp', 'password')
        self.ftpSettings['path'] = self.configStuff('ftp', 'path')

    def dbSettings(self, dbName=None):
        if dbName:
            self.settings['database'] = dbName
            # self.tasks.update(dbName)
        self.settings['defaultUsers'] = self.configStuff(self.settings['database'], 'defaultUsers')

    def gitVars(self):
        try:
            if self.basePath:
                os.chdir(os.path.join(os.path.abspath(sys.path[0]), self.basePath))
            self.git['branch'] = subprocess.check_output("git rev-parse --abbrev-ref HEAD", shell=True)
            self.git['status'] = subprocess.check_output("git status", shell=True)
            self.git['repoVersion'] = subprocess.check_output("cat templates\key~1.TXT|grep ktsTag=", shell=True).replace('@ktsTag=','').replace(';','')
            self.git['lastLog'] = subprocess.check_output("git log -1", shell=True)
        except subprocess.CalledProcessError:
            self.git['branch'] = ''
            self.git['status'] = ''
            self.git['repoVersion'] = ''
            self.git['lastLog'] = ''
        try:
            self.git['ktsVersion'] = self.sqlQuery("select dbo.readKeyCode(1,'@ktsTag=')")['rows'][0][0]
        except KeyError:
            self.git['ktsVersion'] = 'Unknown'

    def menuShow(self, subMenu):
        print
        for x in subMenu.items():
            print x[0].rjust(20), '-', x[1]['description']

    def getMenuName(self,keyword,menus):
        for item in menus.items():
            if keyword in item[1]['keywords']:
                return item[0]

    def runMenuFunction(self,command,menuCommands):
        menuName = self.getMenuName(command,menuCommands)
        if menuName:
            function = menuCommands[menuName]['function']
            if hasattr(function,'__call__'):
                function()
            elif hasattr(function[0],'__call__'):
                function[0](function[1])

    def diagnostic_conversionSettings(self):
        settings = self.command_testConnection(False)['dict']
        requiredSettings = self.conversionSettings
        for x in requiredSettings:
            try:
                print '     %s = %s' % (x.rjust(30), settings[x])
            except KeyError:
                print '     %s = %s' % (x.rjust(30), '*** MISSING ***')

    def diagnostic_auto(self):
        settings = self.command_testConnection(False)
        requiredSettings = self.conversionSettings
        for x in requiredSettings:
            if x not in settings['dict']:
                print x, 'setting was not found'
                return

        conversionProcs = [
            'mikeGLedgerBanks',
            'mikeGLedgerFunds',
            'mikeSource',
            'mikeClerksFundList',
            'mikeFund',
            'mikeOfficers',
            'mikeTrustPurpose',
            # mikeTaxRates
            # mikeTaxroll
            # mikeVouchersOutstanding
            # mikeWarrantsOutstanding
        ]
        for step in conversionProcs:
            print '  ===> %s ===> ' % step, self.sqlQuery("exec dbo.conversion_%s @method = 'fix'" % step, True)['code']

    def diagnostic_fix(self,mode='light'):
        if len(self.command) == 3:
            menuInt = str(self.command[2])
            fixProcName = self.sqlQuery("select fixProc from dbo.diagnosticsBRW('%s',0) where menuInt = %s" % (mode,menuInt))['rows'][0][0]
            sqlcmd = "exec dbo.%s @method = 'fix'" % fixProcName
            print 'running diagnostic fix for %s number %s...' % (mode,menuInt)
            print sqlcmd, self.sqlQuery(sqlcmd,True)['code']

    def diagnostics_show(self,theClass=None):
        sqlcmd = "select display, menuInt from dbo.diagnosticsBRW('%s',0) where code = 1 order by ord" % theClass
        result = self.sqlQuery(sqlcmd)
        if len(result['rows']) > 0:
            for row in result['rows']:
                if not '~' in row[0]:
                    print
                print isnull(row[1]).rjust(5),row[0].ljust(30)
        else:
            print 'nothing to report'.rjust(30)
        print

    def diagnostic_run(self,mode='light',show=True):
        print 'run %s diagnostic battery...' % mode, self.sqlQuery("exec dbo.diagnostics @mode='%s', @storeResults='TRUE', @verbose='FALSE'" % mode,True)['code']
        if show:
            self.diagnostics_show(mode)

    def ftp_settings(self):
        for x in self.ftpSettings:
            print x, self.ftpSettings[x]

    def ftp_put(self, fileName=None):
        files = self.ftpFiles()

        def thePut(fileName):
            ftpSet = self.ftpSettings
            session = ftplib.FTP(ftpSet['host'], ftpSet['user'], ftpSet['password'])
            print '     Sending %s to %s.....' % (fileName, ftpSet['host'])
            try:
                file = open('%s\%s' % (ftpSet['path'], fileName), 'rb')
            except IOError:
                session.quit()
                print '     Failed to locate %s' % fileName
                return
            session.storbinary('STOR %s' % fileName, file)
            file.close()
            session.quit()
            print '     Done :) ... Have a nice day.'

        if len(self.command) == 3:
            fileId = int(self.command[2])
            thePut(files[fileId]['name'])
        elif fileName:
            thePut(fileName)

    def cp(self):
        cmd = self.command
        menuName = self.getMenuName(cmd[0],self.commands)
        subMenu = self.commands[menuName]['subMenu']
        if len(cmd) == 2:
            subMenu[cmd[1]]['function']()
        elif len(cmd) > 2:
            subMenu[cmd[1]]['function'](cmd[2:])
        self.tasks.show(self.settings['database'])
        self.menuShow(subMenu)

    def ftpFiles(self):
        files = {}
        listdir = []
        try:
            listdir = os.listdir(self.ftpSettings['path'])
        except WindowsError, e:
            print 'Oops... ', e
            return files

        for id, file in enumerate(listdir):
            fileToken = {}
            fileToken['name'] = file
            fileToken['size'] = os.path.getsize('%s/%s' % (self.ftpSettings['path'], file))
            files[id + 1] = fileToken
        return files

    def ftp_show(self):
        files = self.ftpFiles()
        menuName = self.getMenuName(self.command[0], self.commands)
        subMenu = self.commands[menuName]['subMenu']
        for file in files.items():
            print '     %s. %-*s %s mb' % (str(file[0]).rjust(3), 30, file[1]['name'], str(round(file[1]['size'] / 1024.0 / 1024.0, 2)).rjust(10))
        if len(self.command) == 1:
            self.menuShow(subMenu)
        elif len(self.command) > 1:
            self.runMenuFunction(self.command[1], subMenu)

    def configStuff(self, section, setting, method='GET', newValue=None):
        if method == 'GET':
            returnValue = ''
            self.defaultUserConfig = ConfigParser.RawConfigParser()
            self.defaultUserConfig.read(self.defaultFileName)
            try:
                returnValue = self.defaultUserConfig.get(section, setting)
            except (ConfigParser.NoSectionError, ConfigParser.NoOptionError):
                returnValue = ''
            return returnValue
        elif method == 'PUT':
            try:
                self.defaultUserConfig.add_section(section)
            except ConfigParser.DuplicateSectionError:
                pass
            self.defaultUserConfig.set(section, setting, newValue)
            with open(self.defaultFileName, 'wb') as configfile:
                self.defaultUserConfig.write(configfile)
            self.dbSettings()


    def command_users(self):
        if len(self.command) == 1:
            if not self.settings['defaultUsers'] > '':
                print 'no default user configuration... (%s)' % self.defaultFileName
                self.sendCommand('user set')
            else:
                for fullName in self.settings['defaultUsers'].split(','):
                    print fullName
        elif self.command[1] == 'set':
            usernames = self.ask('enter the default user names (first last, first last, etc...)')
            self.configStuff(self.settings['database'], 'defaultUsers', 'PUT', usernames)
        elif self.command[1] == 'import' and self.settings['defaultUsers'] > '':
            print 'running dbo.createGroups with defaultUsers', self.sqlQuery("exec dbo.createGroups '%s'" % self.settings['defaultUsers'],True)['code']

    def command_backupNow(self):
        self.command_backup(True)

    def command_backup(self, bypassConfirmation=False):
        def doit():
            print "back up SQL data...", self.sqlQuery("exec dbo.sqlBackup @returnRows='FALSE'", isProc=True, testConnection=True)['code']

        if bypassConfirmation:
            doit()
        else:
            backupFileName = self.sqlQuery("select path from dbo.paths() where name = 'backup'")['rows'][0][0]
            print "do you wish to backup the DB to..."
            if self.ask("%s?" % backupFileName) in ('yes', 'y'):
                doit()

    def command_restore(self):
        files = self.ftpFiles()
        menuName = self.getMenuName(self.command[0],self.commands)
        subMenu = self.commands[menuName]['subMenu']
        print
        for file in files.items():
            print '     %s. %-*s %s mb' % (str(file[0]).rjust(3), 30, file[1]['name'], str(round(file[1]['size'] / 1024.0 / 1024.0, 2)).rjust(10))
        if len(self.command) == 1:
            print "\n     restore X ..."
            self.menuShow(subMenu)
        elif len(self.command) > 1:
            bakRow = files[int(self.command[1])]
            print '   ok restoring ', bakRow
            if areYouSure():
                db = self.settings['database']
                file = '%s\%s' % (self.ftpSettings['path'], bakRow['name'])
                print "kill connections...", self.sqlQuery("alter database %s set single_user with rollback immediate" % db, True, 'Master')['code']
                print "drop database %s" % db, self.sqlQuery("drop database %s" % db, True, 'Master')['code']
                # print "restore database %s from disk='%s'" % (db, file), self.sqlQuery("restore database %s from disk='%s' with move, replace" % (db, file), True, 'Master')['code']
                sql = "declare @defaultLocation varchar(max),@dataName varchar(max),@dataFileName varchar(max)," \
                      "@logName varchar(max),@logFileName varchar(max);" \
                      "select @defaultLocation = " \
                      " substring(physical_name, 1, charindex(N'master.mdf', LOWER(physical_name)) - 1)" \
                      " from master.sys.master_files where database_id = 1 AND file_id = 1;" \
                      "declare @fileListTable table(" \
                      "LogicalName nvarchar(128),PhysicalName nvarchar(260),[Type] char(1),FileGroupName nvarchar(128)," \
                      "Size numeric(20,0),MaxSize numeric(20,0),FileID bigint,CreateLSN numeric(25,0),DropLSN numeric(25,0)," \
                      "UniqueID uniqueidentifier,ReadOnlyLSN numeric(25,0),ReadWriteLSN numeric(25,0),BackupSizeInBytes bigint," \
                      "SourceBlockSize int,FileGroupID int,LogGroupGUID uniqueidentifier,DifferentialBaseLSN numeric(25,0)," \
                      "DifferentialBaseGUID uniqueidentifier,IsReadOnl bit,IsPresent bit,TDEThumbprint varbinary(32));" \
                      "insert into @fileListTable exec ('restore filelistonly from disk=''%s''');" \
                      "select @dataName=LogicalName,@dataFileName = @defaultLocation + LogicalName + '.mdf' from @fileListTable where [TYPE] = 'D';" \
                      "select @logName=LogicalName,@logFileName = @defaultLocation + LogicalName + '.ldf' from @fileListTable where [TYPE] = 'L';" \
                      "restore database %s from disk='%s' with move @dataName to @dataFileName, move @logName to @logFileName," \
                      "recovery,replace;" % (file, db, file)
                result = self.sqlQuery(sql, True, 'Master', True)
                print 'result', result['code']

    def ask(self, question='what do you need?'):
        try:
            commandEntered = raw_input("     %s ===> " % question)
        except KeyboardInterrupt:
            self.command_exit()
        return commandEntered

    def command_diagnostics(self,mode='light'):
        menuName = self.getMenuName(self.command[0],self.commands)
        subMenu = self.commands[menuName]['subMenu']
        if len(self.command) == 1:
            self.diagnostics_show(mode)
            self.menuShow(subMenu)
        elif len(self.command) > 1:
            self.runMenuFunction(self.command[1],subMenu)

    def command_initialSetup(self):
        def setup_db(db):
            sqlCmd = "alter database %s set single_user with rollback immediate" % db
            print 'test for connections to database %s...' % db, self.sqlQuery(sqlCmd,True,'master')['code']
            print 'drop database...', self.sqlQuery("drop database %s" % db,True,'master')['code']
            print 'create database...', self.sqlQuery("create database %s" % db,True,'master')['code']
        def setup_login(db):
            print 'drop login...', self.sqlQuery("drop login %sUser" % db,True)['code']
            print 'create login...', self.sqlQuery("create login %sUser WITH PASSWORD=N'KTS', DEFAULT_DATABASE=[master], CHECK_EXPIRATION=OFF, CHECK_POLICY=OFF" % db,True)['code']
            print 'alter role...', self.sqlQuery("exec master..sp_addsrvrolemember @loginame = N'%sUser', @rolename = N'sysadmin'" % db,True)['code']
        def setup_advancedOptions():
            print 'import enableAdvancedSQLOptions...', self.sqlAlterProc('enableAdvancedSQLOptions','Procedure','1')
            print 'Run enableAdvancedSQLOptions...', self.sqlQuery('exec dbo.enableAdvancedSQLOptions',True)['code']
        def setup_core():
            print 'whoAmI...', self.sqlAlterProc('whoAmI','ScalarFunction','99')
            print 'keyCore...', self.sqlAlterProc('keyCore','Script')
            print 'site...', self.sqlAlterProc('site','View','99')
            print 'readstring...', self.sqlAlterProc('readstring','ScalarFunction','1')
            print 'ridread...', self.sqlAlterProc('ridread','ScalarFunction')
            print 'ridwrite...', self.sqlAlterProc('ridwrite','ScalarFunction')
            print 'getSiteBlob...', self.sqlAlterProc('getSiteBlob','ScalarFunction')
            print 'spWriteStringToFile...', self.sqlAlterProc('spWriteStringToFile')
            print 'split...', self.sqlAlterProc('split','TableFunction')
            print 'splitF...', self.sqlAlterProc('splitF','ScalarFunction','99')
            print 'padRight...', self.sqlAlterProc('padRight','ScalarFunction','99')
            print 'padLeft...', self.sqlAlterProc('padLeft','ScalarFunction','99')
            print 'padCenter...', self.sqlAlterProc('padCenter','ScalarFunction','99')
            print 'clariondate...', self.sqlAlterProc('clariondate','ScalarFunction','1')
            print 'clariondate114...', self.sqlAlterProc('clariondate114','ScalarFunction','1')
            print 'dirRead...', self.sqlAlterProc('dirRead','TableFunction','3')
            print 'SqlObjectCompare...', self.sqlAlterProc('SqlObjectCompare','TableFunction','1')
            print 'superTrim...', self.sqlAlterProc('superTrim','ScalarFunction','1')
            print 'superLTrim...', self.sqlAlterProc('superLTrim','ScalarFunction','1')
            print 'superRTrim...', self.sqlAlterProc('superRTrim','ScalarFunction','1')
            print 'settingsCRUD...', self.sqlAlterProc('settingsCRUD','Procedure','99')
            print 'settingsF...', self.sqlAlterProc('settingsF','ScalarFunction','99')
            print 'logit...', self.sqlAlterProc('logit','Procedure','3')
            print 'object dispatcher...', self.sqlAlterProc('keySQLObjectDispatcher')
            print 'createAccountTypes...', self.sqlAlterProc('createAccountTypes','Procedure','99')
            print 'createReceiptTypes...', self.sqlAlterProc('createReceiptTypes','Procedure','99')
            print 'createReasonsToCancel...', self.sqlAlterProc('createReasonsToCancel','Procedure','99')
            print 'createGLCollectionDescriptions...', self.sqlAlterProc('createGLCollectionDescriptions','Procedure','99')
            print 'paymentTypes...', self.sqlAlterProc('paymentTypes','TableFunction','99')
            print 'journalTypes...', self.sqlAlterProc('journalTypes','TableFunction','99')
            print 'glCreateTables...', self.sqlAlterProc('glCreateTables')
            print 'Run glCreateTables...', self.sqlQuery('exec dbo.glCreateTables',True)['code']
            print 'glAccounts...', self.sqlAlterProc('glAccounts','View','99')
            print 'glAccountVerification...', self.sqlAlterProc('glAccountVerification','Procedure','99')
            print 'creates...', self.sqlAlterProc('createPayCodes','Procedure','99')
            print 'Run createPayCodes...', self.sqlQuery('exec dbo.createPayCodes',True)['code']
            print 'diagnostics...', self.sqlAlterProc('diagnostics','Procedure','99')
            print 'dir...', self.sqlAlterProc('dir','TableFunction')
            print 'spOverwriteTextFile...', self.sqlAlterProc('spOverwriteTextFile')
            print 'spReadTextFile...', self.sqlAlterProc('spReadTextFile')
            print 'keySqlObjectWriteToRepo...', self.sqlAlterProc('keySqlObjectWriteToRepo')
            print 'keyTemplateUpdateFromRepo...', self.sqlAlterProc('keyTemplateUpdateFromRepo','Procedure','3')
            print 'keyTemplateWriteToRepo...', self.sqlAlterProc('keyTemplateWriteToRepo')
            print 'dtypeCommentCRUD...', self.sqlAlterProc('dtypeCommentCRUD','Procedure','99')
            print 'glDetailSync...', self.sqlAlterProc('glDetailSync','Procedure','99')
            print 'keySqlObjectWriteToRepoTR...', self.sqlAlterProc('keySqlObjectWriteToRepoTR','Trigger')
            print 'keyTemplateWriteToRepoTR...', self.sqlAlterProc('keyTemplateWriteToRepoTR','Trigger')
            print 'keySQLObjectCreateAll...', self.sqlAlterProc('keySQLObjectCreateAll','Procedure','3')
            print 'paths...', self.sqlAlterProc('paths','TableFunction','99')
            print 'proper...', self.sqlAlterProc('proper', 'ScalarFunction', '99')
            print 'getInitialsFromFullName...', self.sqlAlterProc('getInitialsFromFullName', 'ScalarFunction', '99')

            self.sendCommand('set gitpath')
            if self.ask('Ready for initial import?') in ('y', 'yes'):
                self.command_import(True)

        if len(self.command) > 1:
            setupStep = self.command[1]
            if setupStep in ('db','database'):
                print "This routine will attempt to drop the database %s" % self.settings['database']
                if self.ask("are you sure you want to proceed?") in ('yes','y'):
                   setup_db(self.settings['database'])
            elif setupStep in ('login'):
                setup_login(self.settings['database'])
            elif setupStep in ('advanced'):
                setup_advancedOptions()
            elif setupStep in ('core'):
                setup_core()

    def command_importSqlObject(self):
        if len(self.command) == 2:
            objName = self.command[1]
            print 'importing %s' % objName, self.sqlQuery("exec dbo.keySQLObjectUpdateFromRepo '%s'" % objName,True)

    def createCommand(self,commandName,keywords,description='',function='',parentMenu=None, chatFunction=None):
        if parentMenu is None:
            self.commands[commandName] = {'keywords':keywords,'description':description,'function':function,'chatFunction':chatFunction,'subMenu':{}}
        else:
            self.commands[parentMenu]['subMenu'][commandName] = {'keywords':keywords,'description':description,'function':function,'chatFunction':chatFunction}
            
    def commandCheck(self,targetCommand):
        if self.command[0] in self.commands[targetCommand]['keywords']:
            return True
        else:
            return False

    def sendCommand(self, command):
        self.command = command.split()
        if len(self.command) < 1:
            return True
        self.runMenuFunction(self.command[0],self.commands)
        return True

    def command_import(self, initialSetup=False):
        def theMeat():
            print 'ok here goes...'
            self.sqlAlterProc("keySQLObjectDispatcher")
            self.sqlAlterProc("keyUpdateAll",'Procedure',"9999")
            result = self.sqlQuery("exec dbo.keyUpdateAll 'NewMethod','FALSE'",True)
            print 'running dbo.keyUpdateAll', result['code']
            print 'running keySQLObjectCreateAll', self.sqlQuery('exec dbo.keySQLObjectCreateAll',True)['code']
            print 'running dbo.keyTemplateUpdateFromRepo', self.sqlQuery("exec dbo.keyTemplateUpdateFromRepo null",True)['code']
            print 'Run glCreateTables...', self.sqlQuery('exec dbo.glCreateTables',True)['code']
            self.sqlAlterProc("createIndexes","Procedure","99")
            print 'running dbo.createIndexes', self.sqlQuery("exec dbo.createIndexes",True)['code']
            self.sqlAlterProc("createGroups","Procedure","99")
            if initialSetup and self.settings['defaultUsers'] > '':
                print 'running dbo.createGroups with defaultUsers', self.sqlQuery("exec dbo.createGroups '%s'" % self.settings['defaultUsers'],True)['code']
            else:
                print 'running dbo.createGroups', self.sqlQuery("exec dbo.createGroups",True)['code']

        connTest = self.command_testConnection(False)
        if connTest['code'] == 1:
            print 'unable to connect to database, can not continue.'
            return
        try:
            connTest['dict']['git.gitpath']
        except KeyError:
            print 'missing needed git settings, can not continue.'
            return
        else:
            theMeat()

    def printRows(self,rows,noneFoundMessage='sorry no rows found'):
        if len(rows) > 0 and rows[0][0] != 'execution failed':
            for row in rows:
                print row
        else:
            print noneFoundMessage
            print

    def diag_sqlObjects(self,method='checkCommand'):
        def runFix():
            print self.sqlQuery("exec dbo.diagFix_SQLObjects @method='fix'")['rows'][0][0]
        def printStatus():
            print self.sqlQuery("declare @message varchar(max), @tally int; exec dbo.diagFix_SQLObjects @message = @message output, @tally = @tally output; select '@message='+@message+';@tally='+cast(@tally as varchar)+';'")['rows'][0][0]
        if method == 'print':
            printStatus()
            return
        elif method == 'checkCommand':
            if len(self.command) == 1:
                printStatus()
            else:
                if self.command[1] == 'fix':
                    runFix()
                printStatus()

    def command_gitCheckout(self):
        cmd = self.command[1:]
        if len(cmd) == 1:
            if areYouSure():
                for x in self.gitCheckout(cmd[0]):
                    print x

    def chat_gitCheckout(self):
        cmd = self.chatObj['cmd'][1:]
        return self.gitCheckout(cmd[0])

    def gitCheckout(self, tag):
        fetchResponse = subprocess.check_output("git fetch --all", shell=True)
        checkoutResonse = subprocess.check_output("git checkout %s" % tag, shell=True)
        return [fetchResponse, checkoutResonse]

    def command_gitpush(self):
        self.sendCommand('git push origin %s' % self.git['branch'])
        self.sendCommand('git push github %s' % self.git['branch'])

    def command_git(self, commandOverride=None):
        try:
            print subprocess.check_output(' '.join(commandOverride or self.command), shell=True)
        except subprocess.CalledProcessError:
            print 'error running subprocess...'

    def command_testConnection(self,display=True):
        result = {}
        gitDict = {}
        try:
            rows = self.sqlQuery("select settingName, settingValue from settings where dbo.splitF(settingName,'.',1) in ('git','conversion','logging')")['rows']
        except KeyError:
            print 'unable to locate settings, probably because the SQL environment is not working yet.'
            return
        if len(rows) > 0 and rows[0][0] != 'execution failed':
            result['code'] = 0
            for row in rows:
                gitDict[row[0]] = row[1]
        else:
            result['code'] = 1
        result['rows'] = rows
        result['dict'] = gitDict
        if display:
           self.printRows(rows,'no git settings found')
        return result

    def chat_help(self):
        return self.chatCommands()

    def command_help(self):
        print
        for help in self.commands.items():
            if help[1]['description'] > '  0':
                print help[0].rjust(20), '-', help[1]['description']
        print

    def command_exit(self):
        sys.exit(0)

    def command_displayMenu(self):
        self.display()

    def chat_displayMenu(self):
        self.gitVars()
        return [
            {'server': self.settings['server'], 'database': self.settings['database']},
            {'ktsVersion': self.git['ktsVersion'], 'repoVersion': self.git['repoVersion']},
            self.git['lastLog'],
        ]

    def command_setSetting(self, prefix, defaultValue=None, newValue=None, settingsCRUD=True, settingName=None):
        name = settingName or self.command[1]
        if not newValue:
            if defaultValue:
                print 'leave blank for default value (%s)' % defaultValue
            newValue = raw_input('Enter %s ==> ' % self.command[1]) or defaultValue
        if settingsCRUD:
            self.sqlQuery("exec dbo.settingsCRUD '%s.%s','%s'" % (prefix, name, newValue), True)
        return newValue
        
    def command_serverSettings(self):
        if len(self.command) < 2:
            return

        setting = self.command[1]
        value = None

        if len(self.command) > 2:
            value = self.command[2]

        if setting in ('db', 'database'):
            self.dbSettings(setting)
            self.configStuff('importDefaults', 'database', 'PUT', value)

        elif setting in ('user', 'username', 'uid'):
            self.setVars('uid', value)
            self.configStuff('importDefaults', 'uid', 'PUT', value)

        elif setting in ('pwd', 'pass', 'password'):
            self.setVars('password', value)
            self.configStuff('importDefaults', 'password', 'PUT', value)

        elif setting in ('server', 'location', 'url'):
            self.setVars('server', value)
            self.configStuff('importDefaults', 'server', 'PUT', value)

        elif setting == 'gitpath':
            self.command_setSetting('git', defaultValue='c:\client\key\kts', newValue=value)

        elif setting == 'gitcommitter':
            self.command_setSetting('git', newValue=value)

        elif setting in ('mikepath', 'mikepathtax'):
            self.command_setSetting('conversion', defaultValue='c:\client\dosdata\ctpro\online', newValue=value)

        elif setting in ('taxyear','officialbankcode','initials','conversiondate','cutoffdate'):
            self.command_setSetting('conversion', newValue=value)

        elif setting in ('ftphost', 'ftpuser', 'ftppassword', 'ftppath'):
            if setting == 'ftppath':
                newValue = self.command_setSetting('ftp', defaultValue='c:\client\key\sqlBackup', newValue=value)
            else:
                newValue = self.command_setSetting('ftp', newValue=value)
            self.configStuff('ftp', self.command[1].replace('ftp', ''), 'PUT', newValue)
            self.ftpSettingsInit()

        elif setting in ('aamasterpath', 'gsipath'):
            self.command_setSetting('conversion', newValue=value)

        elif setting.lower() == 'apiurl':
            if not value:
                value = areYouSure('Enter new apiUrl', boolean=False)
            if areYouSure():
                print "updating Site Setting...", self.sqlQuery("update object set b13 = '%s' where typ=40" % value, True)['code']
        elif setting.lower() == 'apisitecode':
            if not value:
                value = areYouSure('Enter new apiSiteCode', boolean=False)
            if areYouSure():
                print "updating Site Setting...", self.sqlQuery("update object set b12 = '%s' where typ=40" % value, True)['code']
        elif setting.lower() == 'apikey':
            if not value:
                value = areYouSure('Enter new apiKey', boolean=False)
            if areYouSure():
                print "updating Site Setting...", self.sqlQuery("update object set b11 = '%s' where typ=40" % value, True)['code']

    def command_logging(self):
        print self.command
        if not len(self.command) > 1:
            return
        if self.command[1] in ('enable','on','start'):
            self.sqlQuery("exec dbo.logit @control='start|1|'",True)
        elif self.command[1] in ('disable','off','stop'):
            self.sqlQuery("exec dbo.logit @control=stop",True)

    def setVars(self,varName,newValue=''):
        print 'set var...'
        if newValue > '  0':
            self.settings[varName] = newValue
        else:
            self.settings[varName] = raw_input('Enter %s ==> ' % varName)

    def display(self):
        os.system('cls')
        self.gitVars()
        print
        print
        print
        print '     ==================================================='
        print '      kts menu'
        print '          server : %s ' % self.settings['server']
        # print '          password : %s ' % self.settings['password']
        print '          database : %s ' % self.settings['database']
        print '          uid : %s ' % self.settings['uid']
        print
#        print '          git.settings : ', self.git
        print '          branch : %s' % self.git['branch'],
        print '          repoVersion : %s' % self.git['repoVersion'],
        print '          ktsVersion : %s' % self.git['ktsVersion']
#        print self.git['status']
        print '     ==================================================='
        print

    def command_kps(self):
        self.kpsTaxroll.load()

    def command_kpsShow(self):
        self.kpsTaxroll.info()

    def tpsSelect(self, sqlString, dbName, verbose=False, connDatabase=None, returnRowsInDictionary=False):
        if not connDatabase:
            aamasterpath = self.settingsF('conversion.aamasterpath')
            connDatabase = '%s\\%s.TPS' % (aamasterpath, dbName)
        connectionString = 'Driver={SoftVelocity Topspeed driver Read-Only (*.tps)};Dbq=%s\!;Datefield=MyDateField|MyOtherDateField;TimeField=MyTimeField|MyOtherTimeField;' % connDatabase
        package = {}
        package['connectionString'] = connectionString
        package['database'] = connDatabase
        package['sqlString'] = sqlString
        if verbose:
            for key, value in package.items():
                print key, value
        connection = pyodbc.connect(connectionString, autocommit=True)
        cursor = connection.cursor()
        try:
            cursor.execute(sqlString)
            rows = cursor.fetchall()
            if returnRowsInDictionary:
                columns = [column[0] for column in cursor.description]
                package['rows'] = []
                for row in rows:
                    package['rows'].append(dict(zip(columns, row)))
            else:
                package['rows'] = rows
            package['description'] = cursor.description
        except (pyodbc.ProgrammingError, pyodbc.Error) as err:
            package['error'] = err
        connection.close()
        return package

    def tpsXXXXadtax(self):
        importFileRaw = self.settingsF('taxroll.importFile')
        importFileName = importFileRaw.split('\\')[-1]
        if list(importFileName)[0] in ('0','1','2','3','4','5','6','7','8','9'):
            importFileNameOld = importFileName
            importFileName = 'renamed_%s' % importFileName
            importPathAndFileName = '%s\\%s' % ('\\'.join(importFileRaw.split('\\')[0:-1]), importFileName)
            if os.path.isfile(importFileRaw):
                shutil.copy2(importFileRaw, importPathAndFileName)
        else:
            importPathAndFileName = importFileRaw
        tableName = importFileName.split('.')[0]

        print 'ok we will attempt to import the data from %s.tps' % tableName
        sql = 'select * from %s' % tableName
        package = self.tpsSelect(sql, tableName, True, importPathAndFileName)
        if 'error' in package:
            print '   oops pyodbc error... %s' % package['error']
        if len(package['rows']) > 0:
            print 'how many? ', len(package['rows'])
            print 'create adtaxCheck...', self.sqlQuery('exec dbo.createAdtaxCheck', True)['code']
            columnNames = ['RECORDTYPE','ADDITIONNUMBER','TOWNSHIPBLOCK','RANGELOT','SECTIONNUMBER','QTRSECTIONNUMBER','PARCELNUMBER','PROPERTYSPLIT','FULLPIDNUMBER','PIDSORTNUMBER','ITEMNUMBER']
            columnNames = columnNames + ['REALTAXYEAR','OWNERNAME','BUSINESSNAME','ADDRESS1','ADDRESS2','ADDRESS3','CITY','STATE','ZIP1','ZIP2','ZIP3','COUNTRY','ORGSCHOOLDISTRICTMAIN','SCHOOLDISTRICTMAIN']
            columnNames = columnNames + ['ORGSCHOOLDISTRICTTAXRATE','SCHOOLDISTRICTTAXRATE','FIREDISTRICT','MORTGAGECODE','OWNERNUMBER','ACRES','LOTS','MFGHOMEASSESSED','GROSSASSESSED','FREEPORTEXEMPTION']
            columnNames = columnNames + ['BASEEXEMPTION','DBLEXEMPTION','EXEMPTION1','EXEMPTION2','EXEMPTION3','NETASSESSEDVALUE','TOTALTAXRATE','ORIGINALTOTALDUE','TOTALDUE','BALANCEDUE','CERTIFICATENUMBER']
            columnNames = columnNames + ['PAIDOFFDATE','PROPERTYLIENCODE1','PROPERTYLIENAMOUNT1','PROPERTYLIENCODE2','PROPERTYLIENAMOUNT2','LASTTRANDATE','TAXCORRECTIONDATE','TAXCORRECTIONINITIALS','FLAG1']
            columnNames = columnNames + ['FLAG2','FLAG3','LEGALDESCRIPTION']
            sqlInsert = "insert adtaxCheck ({columns})".format(columns=', '.join(columnNames))
            tally = 0
            for id, row in enumerate(package['rows']):
                formatedRow = [str(x).replace("'", "''") for x in row]
                sqlSelect = "select '{values}'".format(values="','".join(formatedRow))
                if self.sqlQuery("%s %s" % (sqlInsert, sqlSelect), True)['code'][0] == 0:
                    tally = tally + 1
            print 'ok i inserted %s records' % tally

    def gsiTaxroll(self):
        def map(row):
            source_Type = row[0:1]
            tax_Year = row[1:5]
            account = row[7:15]
            owner_ID = row[15:22]
            owner_Name1 = row[22:62]
            #owner_Name2 = row[62:102]
            owner_MailInfo = row[102:142]
            owner_Address1 = row[142:182]
            owner_Address2 = row[182:222]
            owner_City = row[222:252]
            owner_St = row[252:254]
            owner_Zip = row[254:259]
            owner_Zip2 = row[259:263]
            owner_Country = row[263:303]
            owner_LCD = row[303:311]
            owner_LCI = row[311:314]
            owner_LCT = row[314:320]
            geo_Number = row[320:350]
            other_ID = row[350:380]
            grossAssessed = row[392:401]
            landAssessed = row[401:410]
            improvAssessed = row[410:419]
            mhAssessed = row[419:428]
            penaltyAssessed = row[428:437]
            exempt = row[437:446]
            taxable = row[446:455]
            millage = row[455:461]
            millCode = row[461:545]
            total_Tax = row[545:557]
            streetNumber = row[557:566]
            streetNoSufix = row[567:571]
            streetDirection = row[571:581]
            streetName = row[581:611]
            streetType = row[611:621]
            streetTown = row[621:651]
            hS_Status = row[651:681]
            acres = row[681:687]
            lots = row[687:693]
            addit = row[693:698]
            block = row[698:702]
            lot = row[702:706]
            sec = row[706:708]
            township = row[708:711]
            range = row[711:714]
            qtrSection = row[714:715]
            deedBook = row[715:724]
            deedPage = row[724:733]
            salesPrice = row[733:742]
            mhPrePaidFlag = row[742:743]
            taxroll_LCD = row[743:751]
            taxroll_LCI = row[751:754]
            taxroll_LCT = row[754:760]
            legal = row[760:2760]
            advanceValue = row[2760:2770]
            advanceTax = row[2770:2780]
            millCodeSet = row[380:392]
            return [
                source_Type,
                tax_Year,
                account,
                owner_ID,
                owner_Name1.strip(),    #4
                #owner_Name2,
                owner_MailInfo.strip(), #5
                owner_Address1.strip(), #6
                owner_Address2.strip(), #7
                owner_City.strip(),     #8
                owner_St.strip(),       #9
                owner_Zip,      #10
                owner_Zip2,     #11
                owner_Country.strip(),  #12
                #owner_LCD,
                #owner_LCI,
                #owner_LCT,
                geo_Number.strip(),     #13
                #other_ID,
                #millCodeSet,
                grossAssessed.strip(),  #14
                landAssessed.strip(),   #15
                improvAssessed.strip(),  #16
                mhAssessed.strip(),     #17
                penaltyAssessed.strip(),#18
                exempt.strip(),         #19
                taxable.strip(),        #20
                streetNumber.strip(),   #21
                streetNoSufix.strip(),  #22
                streetDirection.strip(),#23
                streetName.strip(),     #24
                streetType.strip(),     #25
                streetTown.strip(),     #26
                #hS_Status,
                acres.strip(),          #27
                #lots,
                addit.strip(),          #28
                block.strip(),          #29
                lot.strip(),            #30
                sec.strip(),            #31
                township.strip(),       #32
                range.strip(),          #33
                qtrSection.strip(),     #34
                #deedBook,
                #deedPage,
                #salesPrice,     #35
                #mhPrePaidFlag,  #36
                #taxroll_LCD,    #37
                #taxroll_LCI,    #38
                #taxroll_LCT,    #39
                legal.strip(),          #40
                #advanceValue,   #41
                #advanceTax      #42
                millage,
                millCode,
                total_Tax,
                millCodeSet
            ]
        importFileRaw = self.settingsF('taxroll.importFile')
        if not  importFileRaw:
            print 'missing path to gsi file... fail!'
            return
        rows = []
        with open( importFileRaw, 'r') as content_file:
            rawData = content_file.read()
        i = 0
        for row in rawData.split('\n'):
            rows.append(map(row))
        #for x in rows[0:100]:
        #    m = float(x[36])*.000001
        #    t = format(float(x[38])*.01,'.2f')
        #    p = x[21]+' '+x[22]+' '+x[23]+' '+x[24]+' '+x[25]+' '+x[26] + '                                                        '
        #    print x[0],x[1],x[2],x[3],x[4],x[5],x[6],x[7],x[8],x[9],x[10],x[11],x[12],x[13],x[14],x[15],x[16],x[17],x[18],x[19],x[20],p[1:50],x[27],x[28],x[29]+''+x[32],x[31],x[30]+''+x[33],x[34],x[35],m,t,t,t,x[37]

        if len(rows) > 0:
            print 'how many? ', len(rows)
            print 'create adtaxCheck...', self.sqlQuery('exec dbo.createAdtaxCheck', True)['code']
            columnNames = ['recordType','realTaxYear','itemNumber','ownerNumber','ownerName','address1','address2','address3','city','state','zip1','zip2']
            columnNames = columnNames + ['country','fullPidNumber','grossAssessed','landAssessed','improvedAssessed','mfgHomeAssessed','miscAssessed','baseExemption','Exemption3','netAssessedValue','propLoc']
            columnNames = columnNames + ['acres','additionNumber','townshipBlock','sectionNumber','rangeLot','qtrSectionNumber','legalDescription','TOTALTAXRATE','ORIGINALTOTALDUE','TOTALDUE','BALANCEDUE','PIDSORTNUMBER']
            sqlInsert = "insert adtaxCheck ({columns})".format(columns=', '.join(columnNames))
            tally = 0
            for id, row in enumerate(rows):
                formatedRow = self.gsiFormatedRow(row)
                formatedRow = [str(x).replace("'", "''") for x in formatedRow]
                sqlSelect = "select '{values}'".format(values="','".join(formatedRow))
                #print sqlInsert
                #print sqlSelect
                if len(formatedRow) > 1:
                    if self.sqlQuery("%s %s" % (sqlInsert, sqlSelect), True)['code'][0] == 0:
                        tally = tally + 1
            print 'ok i inserted %s records' % tally

            def map(row):
                taxAreaCode = row[0:8]
                taxRate = row[8:47]
                schoolDistrict = row[164:203]
                return[
                    taxAreaCode.strip(),
                    schoolDistrict.strip(),
                    taxRate.strip()
                    ]
            importFileRaw = self.settingsF('taxroll.taxLevyFile')
            if not  importFileRaw:
                print 'missing path to gsi levl file... fail!'
                return
            rows = []
            with open( importFileRaw, 'r') as content_file:
                rawData = content_file.read()
            i = 0
            for row in rawData.split('\n'):
                rows.append(map(row))
            if len(rows) > 0:
                print 'how many? ', len(rows)
                print 'Prep Tax Levy Table...dbo.taxrollCRUD', self.sqlQuery('exec dbo.taxrollCRUD @method=''prepTaxLevy''', True)['code']
                columnNames = ['taxAreaCode','schoolDistrict','taxRate']
                sqlInsert = "insert taxLevyCheck ({columns})".format(columns=', '.join(columnNames))
                tally = 0
                for id, row in enumerate(rows):
                    formatedRow = [str(x).replace("'", "''") for x in row]
                    sqlSelect = "select '{values}'".format(values="','".join(formatedRow))
                    #print sqlInsert
                    #print sqlSelect
                    if len(formatedRow) > 1:
                        if self.sqlQuery("%s %s" % (sqlInsert, sqlSelect), True)['code'][0] == 0:
                            tally = tally + 1
                print 'ok i inserted %s records' % tally
                print 'update school district and tax rates...dbo.taxrollCRUD', self.sqlQuery('exec dbo.taxrollCRUD @method=''setLevy''', True)['code']

    def gsiFormatedRow(self,x):
        try:
            item = x[2]
            m = float(x[36])*.000001
            t = format(float(x[38])*.01,'.2f')
            proploc = x[21]+' '+x[22]+' '+x[23]+' '+x[24]+' '+x[25]+' '+x[26] + '                                                        '
            proploc = proploc.strip()
            acres = format(float(x[27])*.001,'.2f')
            return [x[0],x[1],item,x[3],x[4],x[5],x[6],x[7],x[8],x[9],x[10],x[11],x[12],x[13],x[14],x[15],x[16],x[17],x[18],x[19],x[19],x[20],proploc,acres,x[28],x[32],x[31],x[33],x[34],x[35],m,t,t,t,x[39]]#,x[37]]
        except ValueError, e:
            print e
            return []

    def gsiAamasterCheck(self):
        def map(row):
            county = row[0:2]
            itemNumber = row[2:9]
            nameId = row[10:19]
            name1 = row[20:59]
            name2 = row[60:99]
            mailingInfo = row[100:139]
            add1 = row[140:179]
            add2 = row[180:219]
            city = row[220:249]
            state = row[250:252]
            rawZip = row[252:262]
            zip1 = rawZip.strip().split('-')[0]
            if len(rawZip.strip().split('-')) > 1:
                zip2 = rawZip.strip().split('-')[1]
            else:
                zip2 = ''
            return [
                itemNumber.strip(),
                name1.strip(),
                name2.strip(),
                mailingInfo.strip(),
                add1.strip(),
                add2.strip(),
                city.strip(),
                state.strip(),
                zip1,
                zip2,
            ]

        gsipath = self.settingsF('conversion.gsipath')
        if not gsipath:
            print 'missing path to gsi file... fail!'
            return
        rows = []
        with open(gsipath, 'r') as content_file:
            rawData = content_file.read()
        for row in rawData.split('\n'):
            rows.append(map(row))
        if len(rows) > 0:
            print 'how many? ', len(rows)
            self.aamasterCheckDropAndCreate()
            columnNames = ['autonumber','ownername','businessname','address1','address2','address3','city','state','zip1','zip2']
            sqlInsert = "insert aamasterCheck ({columns})".format(columns=', '.join(columnNames))
            tally = 0
            for id, row in enumerate(rows):
                formatedRow = [str(x).replace("'", "''") for x in row]
                sqlSelect = "select '{values}'".format(values="','".join(formatedRow))
                if self.sqlQuery("%s %s" % (sqlInsert, sqlSelect), True)['code'][0] == 0:
                    tally = tally + 1
            print 'ok i inserted %s records' % tally
            print 'dbo.aamasterCheckInitialize...', self.sqlQuery('exec dbo.aamasterCheckInitialize', True)['code']

    def aamasterCheckVariables(self):
        columns = []
        columns.append('autonumber varchar(50)')
        columns.append('ownername varchar(50)')
        columns.append('businessname varchar(50)')
        columns.append('address1 varchar(50)')
        columns.append('address2 varchar(50)')
        columns.append('address3 varchar(50)')
        columns.append('city varchar(50)')
        columns.append('state varchar(50)')
        columns.append('zip1 varchar(50)')
        columns.append('zip2 varchar(50)')
        columns.append('zip3 varchar(50)')
        columns.append('country varchar(50)')
        columnNames = [x.split(' ')[0] for x in columns]
        uniqueColumns = []
        uniqueColumns.append('brwid int identity(1,1)')
        uniqueColumns.append('selectedFlag int')
        uniqueColumns.append('invoiceId int')
        uniqueColumns.append('adtaxId int')
        uniqueColumns.append('fullpidnumber varchar(50)')
        uniqueColumns.append('taxYear varchar(10)')
        uniqueColumns.append('defaultAddressBlob varchar(max)')
        uniqueColumns.append('balanceDue money')
        uniqueColumns.append('reason varchar(50)')
        uniqueColumns.append('taxrollDetailId int')
        return columns, columnNames, uniqueColumns

    def aamasterCheckDropAndCreate(self):
        columns, columnNames, uniqueColumns = self.aamasterCheckVariables()
        sqlCreateTable = 'create table aamasterCheck({uniqueColumns}, {columns}, kts{ktsColumns})'.format(uniqueColumns=', '.join(uniqueColumns),columns=', '.join(columns), ktsColumns=', kts'.join(columns))
        print 'drop aamasterCheck...', self.sqlQuery('drop table aamasterCheck', True)['code']
        print 'create aamasterCheck...', self.sqlQuery(sqlCreateTable, True)['code']

    def tpsAamasterGetPackage(self):
        fields = {
            'landAssessed': [['LANDASSESSEDVALUE'], 'int'],
            'improvedassessed': [['IMPROVEDASSESSEDVALUE'], 'int'],
            'miscAssessed': [['MISCELLANEOUSASSESSED'], 'int'],
            'propLoc': [['PHYSICALSTREETNUMBER', 'PHYSICALSTREET', 'PHYSICALTOWN'], 'string'],
        }
        aaMasterFields = []
        for key, fieldArray in fields.items():
            for y in fieldArray[0]:
                aaMasterFields.append(y)

        sqlString = "select fullpidnumber, {fields} from aamaster where FULLPIDNUMBER > '  0'".format(fields=', '.join(aaMasterFields))
        package = self.tpsSelect(sqlString, 'aamaster', returnRowsInDictionary=True)
        return package, fields

    def tpsAamasterKey(self):
        if len(self.command) > 2:
            data, fields = self.tpsAamasterGetPackage()
            print 'key', self.command[2]
            for row in data['rows']:
                if row['fullpidnumber'] == self.command[2]:
                    print row

    def tpsAamasterUpdate(self):
        def joinWithSpace(data, fields):
            a = []
            for field in fields:
                if not str(data[field]) == '0':
                    a.append(str(data[field]))
            return ' '.join(a).strip()

        taxYear = areYouSure('enter the tax year please', boolean=False)
        if areYouSure('are you sure you want to run with taxYear = %s?' % taxYear):
            print 'Here we go... AAmaster Update...'
            package, fields = self.tpsAamasterGetPackage()
            # testlist = [
            #     '0000-06-02N-01E-0-010-00',
            #     '0000-04-02N-02E-0-011-00',
            # ]
            tally = 0
            if len(package['rows']) > 0:
                for row in package['rows']:
                    token = []
                    for adtax, aaMasterArray in fields.items():
                        if aaMasterArray[1] == 'string':
                            token.append("%s='%s'" % (adtax, joinWithSpace(row, aaMasterArray[0])))
                        if aaMasterArray[1] == 'int':
                            intVal = str(joinWithSpace(row, aaMasterArray[0]))
                            if intVal < '  0':
                                intVal = '0'
                            token.append("%s=%s" % (adtax, intVal))

                    setString = ', '.join(token)
                    sqlString = "update adtax set %s where realTaxYear = '%s' and fullPidNumber = '%s'" % (setString, taxYear, row['fullpidnumber'])
                    q = self.sqlQuery(sqlString, True)
                    if q['code'][0] == 0:
                        tally += 1
                    else:
                        print 'oops...', q
            print 'ok i sent %s updates' % tally


    def tpsAamasterCheck(self):
        columns, columnNames, uniqueColumns = self.aamasterCheckVariables()
        sqlString = "select {fields} from aamaster".format(fields=', '.join(columnNames))
        aamasterpath = self.settingsF('conversion.aamasterpath')
        if not aamasterpath:
            print 'missing path to aamaster... fail!'
            return
        package = self.tpsSelect(sqlString, 'aamaster')
        if len(package['rows']) > 0:
            print 'how many? ', len(package['rows'])
            self.aamasterCheckDropAndCreate()
            sqlInsert = "insert aamasterCheck ({columns})".format(columns=', '.join(columnNames))
            tally = 0
            for id, row in enumerate(package['rows']):
                formatedRow = [str(x).replace("'", "''") for x in row]
                sqlSelect = "select '{values}'".format(values="','".join(formatedRow))
                if self.sqlQuery("%s %s" % (sqlInsert, sqlSelect), True)['code'][0] == 0:
                    tally = tally + 1
            print 'ok i inserted %s records' % tally
            print 'dbo.aamasterCheckInitialize...', self.sqlQuery('exec dbo.aamasterCheckInitialize', True)['code']

    def settingsF(self, name, default='unknown'):
        try:
            value = self.sqlQuery("select dbo.settingsF('%s','%s')" % (name, default))['rows'][0][0]
        except KeyError:
            return None
        return value

    def sqlQuery(self, sqlString, isProc=False, alternateDatabase=None, testConnection=False, appName='kts.bat'):
        connDatabase = alternateDatabase or self.settings['database']
        connectionString = 'APP=%s;DRIVER={SQL Server};SERVER=%s;DATABASE=%s;UID=%s;PWD=%s' % (appName, self.settings['server'], connDatabase, self.settings['uid'], self.settings['password'])
        package = {}
        package['connectionString'] = connectionString
        package['database'] = connDatabase
        package['sqlString'] = sqlString
        try:
            connection = pyodbc.connect(connectionString, autocommit=True)
        except (pyodbc.ProgrammingError, pyodbc.Error):
            package['code'] = [1, 'Failed to connect to %s' % connDatabase]

        try:
            cursor = connection.cursor()
        except UnboundLocalError:
            package['code'] = [1, 'Failed to connect to %s' % connDatabase]
            return package

        try:
            cursor.execute(sqlString)
        except (pyodbc.DataError, pyodbc.ProgrammingError), err:
            package['code'] = [1, 'Error on Execute %s' % err]
            package['rows'] = [('', '')]
            connection.close()
            return package

        if testConnection:
            while cursor.nextset():
                pass

        if isProc:
            package['code'] = [0, 'ok']
            package['rows'] = [('', '')]
        else:
            try:
                rows = cursor.fetchall()
                package['code'] = [0, 'ok']
                package['rows'] = rows
            except pyodbc.ProgrammingError, err:
                package['code'] = [1, 'Error on Fetch: %s' % err]
                package['rows'] = [('', '')]
        cursor.commit()
        connection.close()
        return package

    def sqlAlterProc(self,object,type='Procedure',order='2'):
        print 'alter proc dbo.%s' % object
        try:
            self.sqlQuery("drop procedure dbo.%s" % object,True)
        except pyodbc.ProgrammingError:
            print 'drop failed...'
            pass
        args = self.settings
        sqlcmd = "sqlcmd -S%s -d%s -U%s -P%s -iSqlObjects\%s~%s~%s.TXT" % (args['server'],args['database'],args['uid'],args['password'],object,type,order)
        try:
            return subprocess.check_output(sqlcmd, shell=True)
        except subprocess.CalledProcessError as error:
            return 'Process FAILED!', error.message


class tasks(ktsMenu):
    def __init__(self, database):
        self.tasks = {}
        self.currentDatabase = ''
        self.update(database)
        self.defaultTasks = {}
        self.defaultTasks['backup'] = ['daily', '23:00']
        # self.defaultTasks['apiInvoices'] = ['daily', '23:00']

    def show(self, database, update=True):
        if update:
            self.update(database)
        for id, task in self.tasks.items():
            print '     %s - %s   next:%s  %s' % (id, task['name'], task['nextTime'], task['status'])

    def update(self, database=None):
        self.tasks.clear()
        if database:
            self.currentDatabase = database
        taskPrefix = 'kp.%s' % self.currentDatabase
        out, err = getTextFromFile(["schTasks", "/query", "/fo", "csv"])
        tally = 0
        for id, line in enumerate(out.split('\n')):
            if taskPrefix in line:
                tally = tally + 1
                task = {}
                taskArray = line.translate(None, '"\\\r').split(',')
                task['name'], task['nextTime'], task['status'] = taskArray[0], taskArray[1], taskArray[2]
                self.tasks[tally] = task

    def delete(self, args=None, askAreYouSure=True):
        if not args:
            return
        if areYouSure(force=askAreYouSure):
            for arg in args:
                taskName = self.tasks[int(arg)]['name'].split('.')[-1]
                myMenu = ktsMenu()
                print 'dbo.scheduledTasksControl delete %s...' % taskName, myMenu.sqlQuery("exec dbo.scheduledTasksControl @method='delete', @name='%s'" % taskName, True)['code']

    def auto(self, args=None):
        myMenu = ktsMenu()
        print myMenu.sqlQuery('select db_name()')
        # for key, detail in self.defaultTasks.items():
        #     print 'schtasks /create /ru "system" /sc %s /tn "kp.%s.%s" /tr "%s" /st %s /f' % (detail[0], self.currentDatabase, key, cmd, detail[1])

    def runTask(self, args=None):
        if not args:
            return
        for arg in args:
            taskName = self.tasks[int(arg)]['name']
            runDos('schtasks /run /tn "%s"' % taskName)