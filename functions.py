import os
import os.path
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
import zipfile
import urllib
import urlparse
import re
# from kirc import *


class ktsMenu():
    def __init__(self, database=None, basePath=None):
        self.settings = {}
        self.ftpSettings = {}
        self.basePath = basePath
        if self.basePath:
            self.defaultFileName = "%s\\..\\ktsConfig.ini" % self.basePath
            self.logFile = "%s\\..\\notice.log" % self.basePath
        else:
            self.defaultFileName = "..\\ktsConfig.ini"
            self.logFile = "..\\notice.log"
        if database:
            self.dbSettings(database)
        else:
            self.dbSettings(self.configStuff('importDefaults', 'database') or 'kts')

        self.settings['server'] = self.configStuff('importDefaults', 'server') or '.'
        self.settings['uid'] = self.configStuff('importDefaults', 'uid')
        self.settings['password'] = self.configStuff('importDefaults', 'password')
        self.settings['driver'] = self.configStuff('importDefaults', 'driver')

        self.settings['noticeName'] = self.settingsF('site.noticeName', 'Unknown')
        self.settings['noticeEnabled'] = self.settingsF('backup.noticeEnable', 'TRUE')
        self.settings['noticeEventLoop'] = self.settingsF('backup.noticeEventLoop', 'TRUE')
        self.settings['apiVerifyFrequencyTime'] = self.settingsF('site.apiVerifyFrequencyTime', 60)

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
        self.createCommand('displayMenu',['m','menu','display','displayMenu','refresh'],'redraw menu',self.command_displayMenu, chatFunction=self.chat_displayMenu)
        self.createCommand('gitCommands',['git'],'run git command',self.command_git)
        self.createCommand('logging',['logging','log','logit'],'modify log settings',self.command_logging)
        self.createCommand('import',['i','import'],'import from repo into your database',self.command_import)
        self.createCommand('diagSQLObjects',['diagsql','diagsqlobjects'],'runs sqlObjects diagnostic',self.diag_sqlObjects)
        self.createCommand('setup',['setup'],'access all the setup options',self.command_initialSetup)
        self.createCommand('importSQLObject',['importsqlobject','importsql'],'import a named sql object from the repo',self.command_importSqlObject)
        self.createCommand('diagnostics',['d','diag','diagnostic','diagnostics'],'access all diagnostic options',self.command_diagnostics)
        self.createCommand('conversion',['c','conv','conversion'],'access all the conversion tools',[self.command_diagnostics,'conversion'])
        self.createCommand('restore',['restore'],'restore sql data to existing db',self.command_restore)
        self.createCommand('backup',['backup','back'],'back up sql data',self.command_backup, chatFunction=self.chat_backup)
        self.createCommand('backupNow',['backupNow',],'back up sql data without an "are you sure" prompt',self.command_backupNow)
        self.createCommand('users',['user','users'],'display or define default users',self.command_users)
        self.createCommand('gitstatus',['gitstatus','status','s'],'preform a git status',[self.command_git,['git','status']])
        self.createCommand('gitpull',['pull','p'],'preform a git log',[self.command_git,['git','pull']])
        self.createCommand('gitpush',['push'],'preform a git push ',self.command_gitpush)
        self.createCommand('ftp',['ftp'],'put a file to the support server',self.ftp_show, chatFunction=self.chat_ftp)
        self.createCommand('gitstatusporcelain',['gsp'],'preform a porcelain git status',self.command_importSpecial)
        self.createCommand('devup',['devup','devon'],'set all developer defaults on your database',self.command_devup)
        self.createCommand('kps',['kps'],'kps upload to API',self.kpsTaxroll.menu)
        self.createCommand('nateTest',['nate'],'test menu option',self.nateTest)
        self.createCommand('compressFile',['compress','compressFile'],'test menu option',self.command_compress)
        self.createCommand('checkoutTag',['checkout'],'fetch and checkout tag',self.command_gitCheckout, chatFunction=self.chat_gitCheckout)

        self.createCommand('api', ['api', 'API', ], 'run api job',self.command_api, chatFunction=self.chat_api)
        self.createCommand('apiSite', ['site', ],'return site info from the api',self.command_apiSite, 'api')
        self.createCommand('apiSettings',['settings','set' ],'return api settings',self.command_apiSettings, 'api')
        self.createCommand('apiResourceControl',['resource','res' ],'toggle api service (api res X)',self.command_apiResourceControl, 'api')
        self.createCommand('apiLooper',['loop','looper' ],'fire up the api looper (api loop X)',self.command_apiLooper, 'api')
        self.createCommand('apiReset',['reset', ],'reset all the rows for resource (api reset X)',self.command_apiReset, 'api')
        self.createCommand('apiService',['service', 'serv'],'start the api Service Event Loop',self.command_apiService, 'api')
        self.createCommand('apiLog',['log', ],'display api Service log',self.command_apiLog, 'api')

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
        self.createCommand('importTaxLv', ['importTaxLv', ], 'copies XXXXtxlv data into kts for invoicing', self.tpsXXXXtxlv, 'conversion')
        self.createCommand('importTaxFee', ['importTaxFee', ], 'copies XXXXinfo data into kts for invoicing', self.tpsXXXXfee, 'conversion')
        self.createCommand('importTaxPay', ['importTaxPay', ], 'copies XXXXpay data into kts for archiving', self.tpsXXXXpay, 'conversion')
        self.createCommand('importTaxNote', ['importTaxNote', ], 'copies XXXXnote data into kts for invoicing', self.tpsXXXXnote, 'conversion')
        self.createCommand('importSpeTax', ['importSpeTax', ], 'copies spetax data into kts for invoicing', self.tpsspetax, 'conversion')
        self.createCommand('importMort', ['importMort', ], 'copies mortg data into kts', self.tpsmort, 'conversion')
        self.createCommand('importGSI', ['importGSI', ], 'copies GSI data into aamasterCheck', self.gsiAamasterCheck, 'conversion')
        self.createCommand('importGSITax', ['importGSITax', ], 'copies TaxRoll data into kts for invoicing', self.gsiTaxroll, 'conversion')
        self.createCommand('importDEFTax', ['importDEFTax', ], 'copies TaxRoll data into kts for invoicing', self.defTaxroll, 'conversion')
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
        self.putFileName = None
        self.ftpThreadOn = False

    def nateTest(self):
        pass

    def doWeNeedToRunTheBackUp(self):
        if not self.settingsF('backup.aaaEnabled', 'TRUE') == 'TRUE':
            return False
        try:
            todaysBackupDatetime = convertSettingTime(self.settingsF('backup.dailyBackupTime'), format='%Y-%m-%d %I%p', addTheDay=True)
        except ValueError:
            self.log('the backup.dailyBackupTime setting is invalid')
            return False
        try:
            lastBackupDateTime = convertSettingTime(self.settingsF('backup.lastBackupDate'))
        except ValueError:
            lastBackupDateTime = convertSettingTime('2000-01-01', format='%Y-%m-%d')

        # print 'last  ', lastBackupDateTime
        # print 'todays', todaysBackupDatetime
        # print 'now   ', currentDatetime()

        #return false if backup is older than todays backup time
        if lastBackupDateTime > todaysBackupDatetime:
            return False
        #return false if its not time to run the backup yet
        elif todaysBackupDatetime > currentDatetime():
            return False
        #return true if it is past the time to run the backup
        elif todaysBackupDatetime < currentDatetime():
            return True
        else:
            return True

    def command_compress(self):
        if len(self.command) == 2:
            fileName = self.command[1:][0]
            compressResult, sizeOfZip = self.compressFile(fileName)
            if compressResult:
                print "congrats, you compressed %s to %s bytes" % (fileName, sizeOfZip)
            else:
                print "sorry, something went wrong compressing %s..." % fileName

    def compressFile(self, fileName, eraseOriginalFile=True):
        if ':\\' in fileName:
            file2Zip = fileName
            zipFile = "%s.%s" % (fileName.split('.')[0], 'zip')
        else:
            file2Zip = '%s\%s' % (self.ftpSettings['path'], fileName)
            zipFile = '%s\%s.%s' % (self.ftpSettings['path'], fileName.split('.')[0], 'zip')
        try:
            with zipfile.ZipFile(zipFile, 'w', zipfile.ZIP_DEFLATED, allowZip64=True) as theZipFile:
                theZipFile.write(file2Zip, os.path.basename(file2Zip))
        except:
            return False, 0

        sizeOfZipFile = os.path.getsize(zipFile)
        if sizeOfZipFile > 1000 and eraseOriginalFile:
            os.remove(file2Zip)

        return True, sizeOfZipFile

    def shouldIListenToThisGuy(self, who):
        host = self.apiSettingsKps['host']
        apiKey = self.apiSettingsKps['key']
        try:
            if who in [x['name'] for x in apiGet(host, apiKey, resource="v2/kts/administrators")['response']]:
                return True, "sure!"
            else:
                return False, "Sorry, I don't know who you are."
        except:
            return False, "Sorry, I don't know who you are, And I can't check my sources at the moment."

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
            foxFieldsCSV = self.settingsF('conversion.%s.fields' % tableName, None)
            foxFields = None
            if foxFieldsCSV:
                foxFields = foxFieldsCSV.split(',')
            if foxFile:
                #print "My Fox Fields: ", foxFields
                fox = importDBF.dbfClass(foxFile, tableName, foxFields)
                fox.load()
                data = fox.get()
                #print "structure: ", data['structure']
                print 'Drop and create %s...' % data['tableName'], self.sqlQuery(data['dropAndCreateTableSQL'], True)['code']
                for row in data['insertRows']:
                    try:
                        self.sqlQuery(row, True)
                    except:
                        print row

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
                securityCheck, message = self.shouldIListenToThisGuy(self.chatObj['from'])
                if not securityCheck:
                    return [message]
                if cmd[2] == 'on':
                    self.apiServiceControl(enableService=True)
                    return [self.apiService]
                elif cmd[2] == 'off':
                    self.apiServiceControl(enableService=False)
                    return [self.apiService]
            else:
                return 'huh?... im expecting "api service on" or "api service off"'
        elif cmd[1] in ('toggle', 'tog'):
            securityCheck, message = self.shouldIListenToThisGuy(self.chatObj['from'])
            if not securityCheck:
                return [message]
            if len(cmd) == 3 and cmd[2].lower() == 'alloff':
                for key, value in self.apiService.items():
                    pass

                    # self.apiResourceToggle(value['resource'])
                return getApiStatus()
            if len(cmd) == 3 and cmd[2].lower() == 'allon':
                pass
            if len(cmd) == 3:
                self.apiResourceToggle(cmd[2])
                return getApiStatus()
        elif cmd[1] in ('log', 'json', 'result') and len(cmd) == 3:
            verb = cmd[1]
            resource = cmd[2]
            securityCheck, message = self.shouldIListenToThisGuy(self.chatObj['from'])
            if not securityCheck:
                return [message]
            if verb == 'log':
                log = self.apiLog(resource)['rows']
                logArray = [x for x in log]
                return logArray
            elif verb in ('json', 'result'):
                if verb == 'json':
                    fileBase = ["apiPost", "json"]
                elif verb == 'result':
                    fileBase = ["apiResult", "tmp"]
                if self.basePath:
                    jsonFileName = "%s\\..\\%s%s.%s" % (self.basePath, fileBase[0], resource, fileBase[1])
                else:
                    jsonFileName = "..\\%s%s.%s" % (fileBase[0], resource, fileBase[1])
                try:
                    jsonFile = open(jsonFileName, "r")
                    jsonDump = jsonFile.read()
                    jsonFileDateTime = time.ctime(os.path.getmtime(jsonFileName))
                    jsonDecoded = urlparse.parse_qs(jsonDump) if verb == 'json' else jsonDump
                    self.irc.psend([jsonFileDateTime, 'Size:%s' % len(jsonDump)])
                    return jsonDecoded
                except Exception as e:
                    return e

        elif cmd[1] in ('batchsize') and len(cmd) == 4:
            resource = cmd[2]
            newSize = cmd[3]
            securityCheck, message = self.shouldIListenToThisGuy(self.chatObj['from'])
            if not securityCheck:
                return [message]
            self.command_setSetting('api', newValue=newSize, settingName="%s.batchsize" % resource)
            return "right on man! your batchsize for %s is now %s" % (resource, self.settingsF("api.%s.batchsize" % resource))

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

    def command_apiLog(self):
        c = self.command[2:]
        if len(c) == 1:
            log = self.apiLog(c[0])
            if len(log['rows']) > 0:
                for row in log['rows']:
                    print "%s" % row[0]

    def apiLog(self, resource):
        q = "select top 10 " \
            "CONVERT(varchar, time, 112)" \
            " + '-' + dbo.padLeft(cast(datepart(HH,time) as varchar),'0',2)" \
            " + ':' + dbo.padLeft(cast(datepart(MINUTE,time) as varchar),'0',2)" \
            " + ':' + dbo.padLeft(cast(datepart(SECOND,time) as varchar),'0',2)" \
            " + ' ' + message from keylog where procname = 'api%s' order by id desc" % resource
        log = self.sqlQuery(q)
        return log

    def command_apiService(self):
        s = self.apiService
        print 'api Service running: %s (%s)' % (s['running'], s['odometer'])
        if s['running']:
            if areYouSure('do you want to turn this service off?'):
                self.apiServiceControl(enableService=False)
        else:
            if areYouSure('do you want to turn this service on?'):
                self.apiServiceControl(enableService=True)

    def log(self, message):
        # pass
        if isinstance(message, list):
            message = ', '.join(message)
        try:
            file = open(self.logFile, "a")
            file.write("%s\n" % message)
            file.close()
        except IOError:
            pass

    def bulletProofApiServiceEventLoop(self):
        s = self.apiService
        # bail if service is already running
        if s['running']:
            return

        checkinTimer = stopWatch()
        apiVerifyTimer = stopWatch()

        # turn on the lights
        s['running'] = True

        while True:
            # check to see if someone turned off the light
            if not s['running']:
                break

            # API Services
            try:
                self.apiServiceEvent()
            except Exception as e:
                self.log(['failed apiServiceEvent()...', e])
                s['eventRunning'] = False

            if self.settings['noticeEnabled'] == 'TRUE':
                # so every hour, check in with IRC let everyone know whats going on.
                #   but only if notice is enabled
                if checkinTimer.elaps() > 3600:
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
                    self.irc.psend("Hi there, I'm just checking in...")
                    for row in apiStatus:
                        self.irc.psend(row)
                    checkinTimer.reset()

                # so every X minutes we will run apiVerify if the settings and the function exists
                if apiVerifyTimer.elaps() > (self.settings['apiVerifyFrequencyTime'] * (60)):   
                    apiVerifyTimer.reset()
                    self.irc.psend("Hi there, I am thinking now would be a good time to run an apiVerify(). I'll let you know how it goes...")
                    apiVerifyQuery = """declare @message varchar(max), @tally int;
                    EXEC dbo.apiVerify @resetAll='FALSE', @invoiceFlags = @tally OUTPUT, @message = @message OUTPUT;
                    SELECT @tally, @message;"""
                    try:
                        vResult = self.sqlQuery(apiVerifyQuery)['rows']
                    except KeyError:
                        self.irc.psend("Oops, something when wrong with the apiVerify()!!!")
                    if len(vResult) > 0:
                        self.irc.psend(vResult[0][0])
            
        # turn the lights off when going out the door
        s['running'] = False

    def setIRC(self, irc):
        self.irc = irc

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

    def theFTPPutConsoleThread(self):
        print '     Sending %s to %s.....' % (self.putFileName, self.ftpSettings['host'])
        print self.theFTPPut()[1]

    def theFTPPut(self):
        fileName = self.putFileName
        ftpSet = self.ftpSettings
        try:
            session = ftplib.FTP(ftpSet['host'], ftpSet['user'], ftpSet['password'])
        except Exception as e:
            return False, e
        try:
            file = open('%s\%s' % (ftpSet['path'], fileName), 'rb')
        except IOError:
            session.quit()
            return False, 'Failed to locate %s' % fileName
        session.storbinary('STOR %s' % fileName, file)
        file.close()
        session.quit()
        return True, 'Done :) ... Have a nice day.'

    def ftp_put(self, fileName=None):
        files = self.ftpFiles()
        if len(self.command) == 3:
            fileId = int(self.command[2])
            self.putFileName = files[fileId]['name']
            self.threadit("ftp", self.theFTPPutConsoleThread)
        elif fileName:
            self.putFileName = fileName
            self.threadit("ftp", self.theFTPPutConsoleThread)

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

    def ftpFilesDisplay(self):
        fileDisplay = []
        files = self.ftpFiles()
        for file in files.items():
            fileDisplay.append('%s. %-*s %s mb' % (str(file[0]).rjust(3), 30, file[1]['name'], str(round(file[1]['size'] / 1024.0 / 1024.0, 2)).rjust(10)))
        return fileDisplay

    def chat_ftp(self):
        cmd = self.chatObj['chatString'].split()
        if len(cmd) == 1:
            return self.ftpFilesDisplay()
        if len(cmd) == 3 and cmd[1] == 'put':
            securityCheck, message = self.shouldIListenToThisGuy(self.chatObj['from'])
            if not securityCheck:
                return [message]
            files = self.ftpFiles()
            fileId = int(cmd[2])
            self.putFileName = files[fileId]['name']
            self.threadit("ftp", self.theFTPPutChatThread)

    def theFTPPutChatThread(self):
        if self.ftpThreadOn:
            self.irc.psend("Sorry FTP Thread already running...")
            return
        self.ftpThreadOn = True
        self.irc.psend("Ok, i have started a background thread to send you %s..." % self.putFileName)
        self.irc.psend("ill let ya know when im done.")
        try:
            ftpResult = self.theFTPPut()
        except Exception as e:
            ftpResult = (False, e)
        self.irc.psend("Hey there, FTP update...")
        self.irc.psend("here is the result... %s" % ftpResult[1])
        self.ftpThreadOn = False

    def ftp_show(self):
        menuName = self.getMenuName(self.command[0], self.commands)
        subMenu = self.commands[menuName]['subMenu']
        for row in self.ftpFilesDisplay():
            print '     %s' % row
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

    def chat_backup(self):
        securityCheck, message = self.shouldIListenToThisGuy(self.chatObj['from'])
        if not securityCheck:
            return [message]
        return self.backupSQLData()

    def backupSQLData(self):
        return "back up SQL data... %s" % self.sqlQuery("exec dbo.sqlBackup @returnRows='FALSE'", isProc=True, testConnection=True)['code']

    def command_backup(self, bypassConfirmation=False):
        if bypassConfirmation:
            self.backupSQLData()
        else:
            backupFileName = self.sqlQuery("select path from dbo.paths() where name = 'backup'")['rows'][0][0]
            print "do you wish to backup the DB to..."
            if self.ask("%s?" % backupFileName) in ('yes', 'y'):
                self.backupSQLData()

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
        securityCheck, message = self.shouldIListenToThisGuy(self.chatObj['from'])
        if not securityCheck:
            return [message]
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
            rows = self.sqlQuery("select settingName, settingValue from settings where dbo.splitF(settingName,'.',1) in ('git','conversion','logging','checkassessor')")['rows']
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
            print package['error']
        connection.close()
#        for key, value in package.items():
#            print key, value
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

    def tpsXXXXtxlv(self):
        importFileRaw = self.settingsF('taxroll.importTaxLevyFile','')
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
        sql = 'select SCHOOLDISTRICTTAXRATE,SCHOOLDISTIRCTMAIN,TREASURERTOTALMILLS,ASSESSORTOTALMILLS,COUNTY4MILL,PERCENTCOUNTY4MILL,COUNTYGENERAL,PERCENTCOUNTYGENERAL,COUNTYBUILDING,PERCENTCOUNTYBUILDING,COUNTYSINKING,PERCENTCOUNTYSINKING,COUNTYHEALTH,PERCENTCOUNTYHEALTH,SCHDISTGENERAL,PERCENTSCHDISTGENERAL,SCHDISTBULDING,PERCENTSCHDISTBULDING,SCHDISTSINKING,PERCENTSCHDISTSINKING,VOTECHGENERAL,PERCENTVOTECHGENERAL,VOTECHBUILDING,PERCENTVOTECHBUILDING,VOTECHSINKING,PERCENTVOTECHSINKING,OTHERNAME1,MILLOTHER1,PERCENTOTHER1,OTHERNAME2,MILLOTHER2,PERCENTOTHER2,OTHERNAME3,MILLOTHER3,PERCENTOTHER3,OTHERNAME4,MILLOTHER4,PERCENTOTHER4,OTHERNAME5,MILLOTHER5,PERCENTOTHER5 from %s' % tableName
        package = self.tpsSelect(sql, tableName, True, importPathAndFileName)
        print 'create TaxLevyImport...', self.sqlQuery('exec dbo.createTaxLevyImport', True)['code']
        if 'error' in package:
            print '   oops pyodbc error... %s' % package['error']
        if len(package['rows']) > 0:
            print 'how many? ', len(package['rows'])
            columnNames = ['SCHOOLDISTRICTTAXRATE','SCHOOLDISTIRCTMAIN','TREASURERTOTALMILLS','ASSESSORTOTALMILLS','COUNTY4MILL','PERCENTCOUNTY4MILL','COUNTYGENERAL','PERCENTCOUNTYGENERAL','COUNTYBUILDING','PERCENTCOUNTYBUILDING']
            columnNames = columnNames + ['COUNTYSINKING','PERCENTCOUNTYSINKING','COUNTYHEALTH','PERCENTCOUNTYHEALTH','SCHDISTGENERAL','PERCENTSCHDISTGENERAL','SCHDISTBULDING','PERCENTSCHDISTBULDING','SCHDISTSINKING','PERCENTSCHDISTSINKING']
            columnNames = columnNames + ['VOTECHGENERAL','PERCENTVOTECHGENERAL','VOTECHBUILDING','PERCENTVOTECHBUILDING','VOTECHSINKING','PERCENTVOTECHSINKING','OTHERNAME1','MILLOTHER1','PERCENTOTHER1']
            columnNames = columnNames + ['OTHERNAME2','MILLOTHER2','PERCENTOTHER2','OTHERNAME3','MILLOTHER3','PERCENTOTHER3','OTHERNAME4','MILLOTHER4','PERCENTOTHER4','OTHERNAME5','MILLOTHER5','PERCENTOTHER5']
            sqlInsert = "insert TaxLevyImport ({columns})".format(columns=', '.join(columnNames))
            tally = 0
            for id, row in enumerate(package['rows']):
                formatedRow = [str(x).replace("'", "''") for x in row]
                sqlSelect = "select '{values}'".format(values="','".join(formatedRow))
                if self.sqlQuery("%s %s" % (sqlInsert, sqlSelect), True)['code'][0] == 0:
                    tally = tally + 1
            print 'ok i inserted %s records' % tally

    def tpsXXXXfee(self):
        importFileRaw = self.settingsF('taxroll.importTaxFeeFile')
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
        sql = 'select ITEMNUMBER,OWNERNAME,PIDSORTNUMBER,FULLPIDNUMBER,MAILINGFEE,LIENFEE,ADVERTISINGFEES,SPECIALASSESSMENTFEE1,SPECIALASSESSMENTFEE2,SPECIALASSESSMENTFEE3,SPECIALASSESSMENTFEE4,SPECIALASSESSMENTFEE5,OTHERFEES,ENTRYDATE,POSTDATE,POSTRECEIPTNUMBER,COMMENT1,COMMENT2 from %s' % tableName
        package = self.tpsSelect(sql, tableName, True, importPathAndFileName)
        if 'error' in package:
            print '   oops pyodbc error... %s' % package['error']
        if len(package['rows']) > 0:
            print 'how many? ', len(package['rows'])
            print 'create TaxFeeImport...', self.sqlQuery('exec dbo.createTaxFeeImport', True)['code']
            columnNames = ['ITEMNUMBER','OWNERNAME','PIDSORTNUMBER','FULLPIDNUMBER','MAILINGFEE','LIENFEE','ADVERTISINGFEES']
            columnNames = columnNames + ['SPECIALASSESSMENTFEE1','SPECIALASSESSMENTFEE2','SPECIALASSESSMENTFEE3','SPECIALASSESSMENTFEE4','SPECIALASSESSMENTFEE5']
            columnNames = columnNames + ['OTHERFEES','ENTRYDATE','POSTDATE','POSTRECEIPTNUMBER','COMMENT1','COMMENT2']
            sqlInsert = "insert TaxFeeImport ({columns})".format(columns=', '.join(columnNames))
            tally = 0
            for id, row in enumerate(package['rows']):
                formatedRow = [str(x).replace("'", "''") for x in row]
                sqlSelect = "select '{values}'".format(values="','".join(formatedRow))
                if self.sqlQuery("%s %s" % (sqlInsert, sqlSelect), True)['code'][0] == 0:
                    tally = tally + 1
            print 'ok i inserted %s records' % tally

    def tpsXXXXpay(self):
        importFileRaw = self.settingsF('taxroll.importTaxPayFile')
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
        sql = 'select AUTONUMKEYFIELD,FULLPIDNUMBER,OWNERNAME,ITEMNUMBER,RECEIPTNUMBER,TAXYEAR,PAYMENTTYPE,SCHOOLDISTMAIN,SCHOOLDISTTAXRATE,TAXAMOUNTPAID,AMOUNTCASH,AMOUNTCHECK,PENALTY,FEESCODE,FEESAMOUNT,BALANCEDUEAFTERPAYMENT,TOTALDUE,PAIDBY,CERTIFICATENUMBER,TRANSACTIONPAIDDATE,POSTEDBY,SYSTEMDATE,SYSTEMTIME from %s' % tableName
        package = self.tpsSelect(sql, tableName, True, importPathAndFileName)
        if 'error' in package:
            print '   oops pyodbc error... %s' % package['error']
        if len(package['rows']) > 0:
            print 'how many? ', len(package['rows'])
            print 'create TaxPayImport...', self.sqlQuery('exec dbo.createTaxPayImport', True)['code']
            columnNames = ['AUTONUMKEYFIELD','FULLPIDNUMBER','OWNERNAME','ITEMNUMBER','RECEIPTNUMBER','TAXYEAR']
            columnNames = columnNames + ['PAYMENTTYPE','SCHOOLDISTMAIN','SCHOOLDISTTAXRATE','TAXAMOUNTPAID','AMOUNTCASH','AMOUNTCHECK']
            columnNames = columnNames + ['PENALTY','FEESCODE','FEESAMOUNT','BALANCEDUEAFTERPAYMENT','TOTALDUE','PAIDBY']
            columnNames = columnNames + ['CERTIFICATENUMBER','TRANSACTIONPAIDDATE','POSTEDBY','SYSTEMDATE','SYSTEMTIME']
            sqlInsert = "insert TaxPayImport ({columns})".format(columns=', '.join(columnNames))
            tally = 0
            for id, row in enumerate(package['rows']):
                formatedRow = [str(x).replace("'", "''") for x in row]
                sqlSelect = "select '{values}'".format(values="','".join(formatedRow))
                if self.sqlQuery("%s %s" % (sqlInsert, sqlSelect), True)['code'][0] == 0:
                    tally = tally + 1
            print 'ok i inserted %s records' % tally

    def tpsXXXXnote(self):
        importFileRaw = self.settingsF('taxroll.importTaxNoteFile')
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
        sql = 'select ITEMNUMBER,USERINITIALS,NOTEDATE,NOTETIME,NOTECODE,ACTIONDATE,NOTE from %s' % tableName
        package = self.tpsSelect(sql, tableName, True, importPathAndFileName)
        if 'error' in package:
            print '   oops pyodbc error... %s' % package['error']
        if len(package['rows']) > 0:
            print 'how many? ', len(package['rows'])
            print 'create TaxNoteImport...', self.sqlQuery('exec dbo.createTaxNoteImport', True)['code']
            columnNames = ['ITEMNUMBER','USERINITIALS','NOTEDATE','NOTETIME','NOTECODE','ACTIONDATE','NOTE']
            sqlInsert = "insert TaxNoteImport ({columns})".format(columns=', '.join(columnNames))
            tally = 0
            for id, row in enumerate(package['rows']):
                formatedRow = [str(x).replace("'", "''") for x in row]
                sqlSelect = "select '{values}'".format(values="','".join(formatedRow))
                if self.sqlQuery("%s %s" % (sqlInsert, sqlSelect), True)['code'][0] == 0:
                    tally = tally + 1
            print 'ok i inserted %s records' % tally

    def tpsspetax(self):
        importFileRaw = self.settingsF('taxroll.importSpeTaxFile')
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
            print 'create SpeTaxImport...', self.sqlQuery('exec dbo.createSpeTaxImport', True)['code']
            columnNames = ['NUMBER','PIDSORTNUMBER','TRANSACTIONDATE','FULLPIDNUMBER','ITEMNUMBER','OWNERNUMBER','OWNERNAME','BUSINESSNAME','ADDRESS1','ADDRESS2']
            columnNames = columnNames + ['CITY','STATE','ZIP1','ZIP2','COUNTRY','SCHOOLDISTRICTTAXRATE','SCHOOLDISTRICTMAIN','SPECIALTAX1','COMMENT1']
            columnNames = columnNames + ['SPECIALTAX2','COMMENT2','SPECIALTAX3','COMMENT3','SPECIALTAX4','COMMENT4','SPECIALTAX5','COMMENT5','SPECIALTAX6','COMMENT6']
            sqlInsert = "insert SpeTaxImport ({columns})".format(columns=', '.join(columnNames))
            tally = 0
            for id, row in enumerate(package['rows']):
                formatedRow = [str(x).replace("'", "''") for x in row]
                sqlSelect = "select '{values}'".format(values="','".join(formatedRow))
                if self.sqlQuery("%s %s" % (sqlInsert, sqlSelect), True)['code'][0] == 0:
                    tally = tally + 1
            print 'ok i inserted %s records' % tally


    def tpsmort(self):
        importFileRaw = self.settingsF('taxroll.importMortFile')
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
            print 'create MortImport...', self.sqlQuery('exec dbo.createMortImport', True)['code']
            columnNames = ['AUTONUMBERKEY','MORTGAGECODE','NAME','ADDRESS1','ADDRESS2']
            columnNames = columnNames + ['CITY','STATE','COUNTRY','ZIP1','ZIP2','ZIP3','PHONEVOICE','PHONEFAX','EMAILADDRESS','CHANGEDATE']
            columnNames = columnNames + ['CHANGEINITIALS','COMMENTS']
            sqlInsert = "insert MortImport ({columns})".format(columns=', '.join(columnNames))
            tally = 0
            for id, row in enumerate(package['rows']):
                formatedRow = [str(x).replace("'", "''") for x in row]
                sqlSelect = "select '{values}'".format(values="','".join(formatedRow))
                if self.sqlQuery("%s %s" % (sqlInsert, sqlSelect), True)['code'][0] == 0:
                    tally = tally + 1
            print 'ok i inserted %s records' % tally


    def gsiTaxroll(self):
        def gsiTrMap():
            d = {
                'source_Type':     {'start':    0, 'end':    1, 'ktsName': 'recordType'},
                'tax_Year':        {'start':    1, 'end':    5, 'ktsName': 'realTaxYear'},
                'account':         {'start':    7, 'end':   15, 'ktsName': 'itemNumber'},
                'owner_ID':        {'start':   15, 'end':   22, 'ktsName': 'ownerNumber'},
                'owner_Name1':     {'start':   22, 'end':   62, 'ktsName': 'ownerName', 'strip': True},
                'owner_Name2':     {'start':   62, 'end':  102, 'ktsName': 'GSI_owner_Name2', 'strip': True},
                'owner_MailInfo':  {'start':  102, 'end':  142, 'ktsName': 'address1', 'strip': True},
                'owner_Address1':  {'start':  142, 'end':  182, 'ktsName': 'address2', 'strip': True},
                'owner_Address2':  {'start':  182, 'end':  222, 'ktsName': 'address3', 'strip': True},
                'owner_City':      {'start':  222, 'end':  252, 'ktsName': 'city', 'strip': True},
                'owner_St':        {'start':  252, 'end':  254, 'ktsName': 'state', 'strip': True},
                'owner_Zip':       {'start':  254, 'end':  259, 'ktsName': 'zip1'},
                'owner_Zip2':      {'start':  259, 'end':  263, 'ktsName': 'zip2'},
                'owner_Country':   {'start':  263, 'end':  303, 'ktsName': 'country', 'strip': True},
                'owner_LCD':       {'start':  303, 'end':  311, 'ktsName': 'GSI_owner_LCD'},
                'owner_LCI':       {'start':  311, 'end':  314, 'ktsName': 'GSI_owner_LCI'},
                'owner_LCT':       {'start':  314, 'end':  320, 'ktsName': 'GSI_owner_LCT'},
                'geo_Number':      {'start':  320, 'end':  350, 'ktsName': 'fullPidNumber', 'strip': True},
                'other_ID':        {'start':  350, 'end':  380, 'ktsName': 'GSI_other_ID'},
                'millCodeSet':     {'start':  380, 'end':  392, 'ktsName': 'PIDSORTNUMBER'},
                'grossAssessed':   {'start':  392, 'end':  401, 'ktsName': 'grossAssessed', 'strip': True},
                'landAssessed':    {'start':  401, 'end':  410, 'ktsName': 'landAssessed', 'strip': True},
                'improvAssessed':  {'start':  410, 'end':  419, 'ktsName': 'improvedAssessed', 'strip': True},
                'mhAssessed':      {'start':  419, 'end':  428, 'ktsName': 'mfgHomeAssessed', 'strip': True},
                'penaltyAssessed': {'start':  428, 'end':  437, 'ktsName': 'miscAssessed', 'strip': True},
                'exempt':          {'start':  437, 'end':  446, 'ktsName': 'baseExemption', 'strip': True},
                'exempt3':         {'start':  437, 'end':  446, 'ktsName': 'Exemption3', 'strip': True},
                'taxable':         {'start':  446, 'end':  455, 'ktsName': 'netAssessedValue', 'strip': True},
                'millage':         {'start':  455, 'end':  461, 'ktsName': 'TOTALTAXRATE', 'float1': True},
                'millCode':        {'start':  461, 'end':  545, 'ktsName': 'GSI_millCode'},
                'total_Tax':       {'start':  545, 'end':  557, 'ktsName': 'ORIGINALTOTALDUE', 'float2': True},
                'KTS_total_Tax2':  {'start':  545, 'end':  557, 'ktsName': 'TOTALDUE', 'float2': True},
                'KTS_total_Tax3':  {'start':  545, 'end':  557, 'ktsName': 'BALANCEDUE', 'float2': True},
                'streetNumber':    {'start':  557, 'end':  566, 'ktsName': 'GSI_streetNumber'},
                'streetNoSufix':   {'start':  567, 'end':  571, 'ktsName': 'GSI_streetNoSufix'},
                'streetDirection': {'start':  571, 'end':  581, 'ktsName': 'GSI_streetDirection'},
                'streetName':      {'start':  581, 'end':  611, 'ktsName': 'GSI_streetName'},
                'streetType':      {'start':  611, 'end':  621, 'ktsName': 'GSI_streetType'},
                'streetTown':      {'start':  621, 'end':  651, 'ktsName': 'GSI_streetTown'},
                'KTS_proploc':     {'start':  557, 'end':  651, 'ktsName': 'propLoc', 'strip': True, 'sub': True},
                'hS_Status':       {'start':  651, 'end':  681, 'ktsName': 'GSI_hS_Status'},
                'acres':           {'start':  681, 'end':  687, 'ktsName': 'acres', 'strip': True, 'float3': True},
                'lots':            {'start':  687, 'end':  693, 'ktsName': 'GSI_lots'},
                'addit':           {'start':  693, 'end':  698, 'ktsName': 'additionNumber', 'strip': True},
                'block':           {'start':  698, 'end':  702, 'ktsName': 'GSI_block'},
                'lot':             {'start':  702, 'end':  706, 'ktsName': 'GSI_lot'},
                'sec':             {'start':  706, 'end':  708, 'ktsName': 'sectionNumber', 'strip': True},
                'township':        {'start':  708, 'end':  711, 'ktsName': 'townshipBlock', 'strip': True},
                'range':           {'start':  711, 'end':  714, 'ktsName': 'rangeLot', 'strip': True},
                'qtrSection':      {'start':  714, 'end':  715, 'ktsName': 'qtrSectionNumber', 'strip': True},
                'deedBook':        {'start':  715, 'end':  724, 'ktsName': 'GSI_deedBook', 'strip': True},
                'deedPage':        {'start':  724, 'end':  733, 'ktsName': 'GSI_deedPage'},
                'salesPrice':      {'start':  733, 'end':  742, 'ktsName': 'GSI_salesPrice'},
                'mhPrePaidFlag':   {'start':  742, 'end':  743, 'ktsName': 'GSI_mhPrePaidFlag'},
                'taxroll_LCD':     {'start':  743, 'end':  751, 'ktsName': 'GSI_taxroll_LCD'},
                'taxroll_LCI':     {'start':  751, 'end':  754, 'ktsName': 'GSI_taxroll_LCI'},
                'taxroll_LCT':     {'start':  754, 'end':  760, 'ktsName': 'GSI_taxroll_LCT'},
                'legal':           {'start':  760, 'end': 2760, 'ktsName': 'legalDescription', 'strip': True},
                'advanceValue':    {'start': 2760, 'end': 2770, 'ktsName': 'GSI_advanceValue'},
                'advanceTax':      {'start': 2770, 'end': 2780, 'ktsName': 'GSI_advanceTax'},
            }
            return d
            
        def mapOld(row):
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
                legal.strip(),          #40  #A36
                #advanceValue,   #41
                #advanceTax      #42
                millage,                #A37
                millCode,               #A38
                total_Tax,              #A39
                millCodeSet             #A40
            ]
            
        def adtaxMap():
            return [
                'recordType',
                'realTaxYear',
                'itemNumber',
                'ownerNumber',
                'ownerName',
                'address1',
                'address2',
                'address3',
                'city',
                'state',
                'zip1',
                'zip2',
                'country',
                'fullPidNumber',
                'grossAssessed',
                'landAssessed',
                'improvedAssessed',
                'mfgHomeAssessed',
                'miscAssessed',
                'baseExemption',
                'Exemption3',
                'netAssessedValue',
                'propLoc',
                'acres',
                'additionNumber',
                'townshipBlock',
                'sectionNumber',
                'rangeLot',
                'qtrSectionNumber',
                'legalDescription',
                'TOTALTAXRATE',
                'ORIGINALTOTALDUE',
                'TOTALDUE',
                'BALANCEDUE',
                'PIDSORTNUMBER',
                'tally',
                'GSI_owner_Name2',
                'GSI_owner_LCD',
                'GSI_owner_LCI',
                'GSI_owner_LCT',
                'GSI_other_ID',
                'GSI_millCode',
                'GSI_streetNumber',
                'GSI_streetNoSufix',
                'GSI_streetDirection',
                'GSI_streetName',
                'GSI_streetType',
                'GSI_streetTown',
                'GSI_hS_Status',
                'GSI_lots',
                'GSI_block',
                'GSI_lot',
                'GSI_deedBook',
                'GSI_deedPage',
                'GSI_salesPrice',
                'GSI_mhPrePaidFlag',
                'GSI_taxroll_LCD',
                'GSI_taxroll_LCI',
                'GSI_taxroll_LCT',
                'GSI_advanceValue',
                'GSI_advanceTax',
            ]

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
                print 'error while formatting row: %s' % e
                return []

        importFileRaw = self.settingsF('taxroll.importFile')
        if not  importFileRaw:
            print 'missing path to gsi file... fail!'
            return
        rows = []
        with open( importFileRaw, 'r') as content_file:
            rawData = content_file.read()
        i = 0
        for row in rawData.split('\n'): # found that some legals contain a hex00 and we end up missing that whole row of data
            rows.append(row)

        if len(rows) > 0:
            print 'how many? ', len(rows)
            print 'create adtaxCheck...', self.sqlQuery('exec dbo.createAdtaxCheck', True)['code']
            # get the adtaxCheck column names from the adtaxMap()
            columnNames = adtaxMap() 
            sqlInsert = "insert adtaxCheck ({columns})".format(columns=', '.join(columnNames))
            tally = 0
            odometer = 0
            for id, row in enumerate(rows):
                odometer = odometer + 1
                # formatedRow = self.gsiFormatedRow(row)
                
                # use the map to divide the row up to fields
                m = gsiTrMap()
                rowObj = {}
                for fld, val in m.items():
                    rowObj[val['ktsName']] = row[val['start']:val['end']]
                    #  dont forget float and stripping as perscribed in the map
                    if val.get('sub'):
                        rowObj[val['ktsName']] = re.sub(' +',' ',rowObj[val['ktsName']])
                    if val.get('strip'):
                        rowObj[val['ktsName']] = rowObj[val['ktsName']].strip()
                    # Float stuff
                    try:
                        if val.get('float1'):
                            if rowObj[val['ktsName']] == '':
                                rowObj[val['ktsName']] = '0'
                            rowObj[val['ktsName']] = float(rowObj[val['ktsName']])*.000001
                        if val.get('float2'):
                            if rowObj[val['ktsName']] == '':
                                rowObj[val['ktsName']] = '0'
                            rowObj[val['ktsName']] = format(float(rowObj[val['ktsName']])*.01,'.2f')
                        if val.get('float3'):
                            if rowObj[val['ktsName']] == '':
                                rowObj[val['ktsName']] = '0'
                            rowObj[val['ktsName']] = format(float(rowObj[val['ktsName']])*.001,'.2f')
                    except ValueError, e:
                        print 'tally#: %s, error while attempting to float fld: %s, val: %s,  error: %s' % (tally, fld, rowObj[val['ktsName']], e)
                        print rowObj
                        
                # get the data arranged into the right order for insert
                #  columnNames is the right order
                formatedRow = []
                for c in columnNames:
                    if c == 'tally':
                        formatedRow.append(tally + 1)
                    else:
                        formatedRow.append(rowObj[c])
                formatedRow = [str(x).replace("'", "''") for x in formatedRow]
                sqlSelect = "select '{values}'".format(values="','".join(formatedRow))
                # print sqlInsert
                # print sqlSelect
                if len(formatedRow) > 1:
                    rslt = self.sqlQuery("%s %s" % (sqlInsert, sqlSelect), True)
                    if rslt['code'][0] == 0:
                        tally = tally + 1
                    else:
                        print '====>'
                        print rslt
                        print '<===='
                else: 
                    print '====>'
                    print 'tally: %s, Failed to insert row...' % tally
                    print row
                    print '<===='
                # print 'current tally: %s    odometer: %s     fmrowLen: %s' % (tally, odometer, len(formatedRow))
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
            importFileRaw = self.settingsF('taxroll.importTaxLevyFile')
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

    def gsiFormatedRowOld(self,x):
        try:
            item = x[2]
            m = float(x[36])*.000001
            t = format(float(x[38])*.01,'.2f')
            proploc = x[21]+' '+x[22]+' '+x[23]+' '+x[24]+' '+x[25]+' '+x[26] + '                                                        '
            proploc = proploc.strip()
            acres = format(float(x[27])*.001,'.2f')
            return [x[0],x[1],item,x[3],x[4],x[5],x[6],x[7],x[8],x[9],x[10],x[11],x[12],x[13],x[14],x[15],x[16],x[17],x[18],x[19],x[19],x[20],proploc,acres,x[28],x[32],x[31],x[33],x[34],x[35],m,t,t,t,x[39]]#,x[37]]
        except ValueError, e:
            print 'error while formatting row: %s' % e
            return []

    def defTaxroll(self):
        def map(row):
            recordtype = row[0:1]
            additionnumber = row[1:5]
            townshipblock = row[5:8]
            rangelot = row[8:11]
            sectionnumber = row[11:13]
            qtrsectionnumber = row[13:14]
            parcelnumber = row[14:17]
            propertysplit = row[17:19]
            fullpidnumber = row[19:59]
            pidsortnumber = row[59:77]
            itemnumber = row[77:85]
            realtaxyear = row[86:90]
            ownername = row[90:130]
            businessname = row[130:170]
            address1 = row[170:210]
            address2 = row[210:250]
            address3 = row[250:290]
            city = row[290:320]
            state = row[320:322]
            zip1 = row[322:327]
            zip2 = row[327:331]
            zip3 = row[331:335]
            country = row[335:365]
            orgschooldistrictmain = row[365:385]
            schooldistrictmain = row[385:405]
            orgschooldistricttaxrate = row[405:425]
            schooldistricttaxrate = row[425:445]
            firedistrict = row[445:460]
            mortgagecode = row[460:467]
            ownernumber = row[467:482]
            acres = row[482:490]
            lots = row[490:496]
            mfghomeassessed = row[496:503]
            grossassessed = row[503:512]
            freeportexemption = row[512:521]
            baseexemption = row[521:530]
            dblexemption = row[530:539]
            exemption1 = row[539:548]
            exemption2 = row[548:557]
            exemption3 = row[557:566]
            netassessedvalue = row[566:575]
            totaltaxrate = row[575:585]
            originaltotaldue = row[585:597]
            totaldue = row[597:609]
            balancedue = row[609:621]
            certificatenumber = row[621:636]
            paidoffdate = row[636:646]
            propertyliencode1 = row[646:651]
            propertylienamount1 = row[651:659]
            propertyliencode2 = row[659:664]
            propertylienamount2 = row[664:672]
            lasttrandate = row[672:682]
            taxcorrectiondate = row[682:692]
            taxcorrectioninitials = row[692:695]
            flag1 = row[695:696]
            flag2 = row[696:697]
            flag3 = row[697:698]
            pertyp = row[698:699]
            proploc = row[699:750]
            mort_cd = row[750:755]
            morleg = row[755:756]
            bankrupt = row[756:757]
            landassessed = row[757:766]
            improvedassessed = row[766:775]
            miscassessed = row[775:784]
            physicalstreetnumber = row[784:834]
            physicalstreet = row[834:884]
            physicaltown = row[884:934]
            physicalstreetdirection = row[934:984]
            legaldescription = row[984:2983]
            return [
                recordtype.strip(),
                additionnumber.strip(),
                townshipblock.strip(),
                rangelot.strip(),
                sectionnumber.strip(),
                qtrsectionnumber.strip(),
                parcelnumber.strip(),
                propertysplit.strip(),
                fullpidnumber.strip(),
                pidsortnumber.strip(),
                itemnumber.strip(),
                realtaxyear.strip(),
                ownername.strip(),
                businessname.strip(),
                address1.strip(),
                address2.strip(),
                address3.strip(),
                city.strip(),
                state.strip(),
                zip1.strip(),
                zip2.strip(),
                zip3.strip(),
                country.strip(),
                orgschooldistrictmain.strip(),
                schooldistrictmain.strip(),
                orgschooldistricttaxrate.strip(),
                schooldistricttaxrate.strip(),
                firedistrict.strip(),
                mortgagecode.strip(),
                ownernumber.strip(),
                acres.strip(),
                lots.strip(),
                mfghomeassessed.strip(),
                grossassessed.strip(),
                freeportexemption.strip(),
                baseexemption.strip(),
                dblexemption.strip(),
                exemption1.strip(),
                exemption2.strip(),
                exemption3.strip(),
                netassessedvalue.strip(),
                totaltaxrate.strip(),
                originaltotaldue.strip(),
                totaldue.strip(),
                balancedue.strip(),
                certificatenumber.strip(),
                paidoffdate.strip(),
                propertyliencode1.strip(),
                propertylienamount1.strip(),
                propertyliencode2.strip(),
                propertylienamount2.strip(),
                lasttrandate.strip(),
                taxcorrectiondate.strip(),
                taxcorrectioninitials.strip(),
                flag1.strip(),
                flag2.strip(),
                flag3.strip(),
                pertyp.strip(),
                proploc.strip(),
                mort_cd.strip(),
                morleg.strip(),
                bankrupt.strip(),
                landassessed.strip(),
                improvedassessed.strip(),
                miscassessed.strip(),
                physicalstreetnumber.strip(),
                physicalstreet.strip(),
                physicaltown.strip(),
                physicalstreetdirection.strip(),
                legaldescription]
        importFileRaw = self.settingsF('taxroll.importFile')
        if not  importFileRaw:
            print 'missing path to tax file... fail!'
            return
        rows = []
        with open( importFileRaw, 'r') as content_file:
            rawData = content_file.read()
            rawData = rawData.replace('""',' ')
        i = 0
        for row in rawData.split('\n'):
            rows.append(map(row))

        if len(rows) > 0:
            print 'how many? ', len(rows)
            print 'create adtaxCheck...', self.sqlQuery('exec dbo.createAdtaxCheck', True)['code']
            columnNames = ['recordType','additionnumber','townshipblock','rangelot','sectionnumber','qtrsectionnumber','parcelnumber','propertysplit']
            columnNames = columnNames + ['fullpidnumber','pidsortnumber','itemnumber']
            columnNames = columnNames + ['realtaxyear','ownername','businessname','address1','address2','address3','city','state','zip1','zip2','zip3']
            columnNames = columnNames + ['country','orgschooldistrictmain','schooldistrictmain','orgschooldistricttaxrate','schooldistricttaxrate','firedistrict']
            columnNames = columnNames + ['mortgagecode','ownernumber','acres']
            columnNames = columnNames + ['lots','mfghomeassessed','grossAssessed','freeportexemption','baseexemption']
            columnNames = columnNames + ['dblexemption','exemption1','exemption2','exemption3','netassessedvalue']
            columnNames = columnNames + ['totaltaxrate','originaltotaldue','totaldue','balancedue','certificatenumber']
            columnNames = columnNames + ['propertyliencode1','propertylienamount1','propertyliencode2','propertylienamount2']
            columnNames = columnNames + ['taxcorrectioninitials','flag1','flag2','flag3','proploc','landassessed','improvedassessed','miscassessed']
            columnNames = columnNames + ['physicalstreetnumber','physicalstreet','physicaltown','physicalstreetdirection','legaldescription']
            sqlInsert = "insert adtaxCheck ({columns})".format(columns=', '.join(columnNames))
            tally = 0
            for id, row in enumerate(rows):
                formatedRow = self.defFormatedRow(row)
                #print formatedRow
                formatedRow = [str(x).replace("'", "''") for x in formatedRow]
                sqlSelect = "select '{values}'".format(values="','".join(formatedRow))
                #print sqlInsert
                #print sqlSelect
                if len(formatedRow) > 1:
                    if self.sqlQuery("%s %s" % (sqlInsert, sqlSelect), True)['code'][0] == 0:
                        tally = tally + 1
            print 'ok i inserted %s records' % tally

            def map(row):
                school = row[0:20]
                millagename = row[20:40]
                taxrate = row[40:70]
                totaltaxrate = row[70:100]
                return[
                    school.strip(),
                    millagename.strip(),
                    taxrate.strip(),
                    totaltaxrate.strip()
                    ]
            importFileRaw = self.settingsF('taxroll.importTaxLevyFile')
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
                print 'Prep Tax Levy Table...dbo.taxrollCRUD', self.sqlQuery('exec dbo.taxrollCRUD @method=''prepTaxLevyDefault''', True)['code']
                columnNames = ['School','MillageName','TaxRate','TotalTaxRate']
                sqlInsert = "insert taxLevyCheckDefault ({columns})".format(columns=', '.join(columnNames))
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


    def defFormatedRow(self,x):
        try:
            if x[10].strip().isdigit():
                it = float(x[10].strip())*1
            else:
                it = 0
            if x[11].strip().isdigit():
                ty = float(x[11].strip())*1
            else:
                ty = 0
            if x[28].isdigit():
                mc = float(x[28].strip())*1
            else:
                mc = 0
            if x[29].isdigit():
                on = float(x[29].strip())*1
            else:
                on = 0
            if x[30].isdigit():
                ac = float(x[30].strip())*1
            else:
                ac = 0
            if x[31].isdigit():
                lt = float(x[31].strip())*1
            else:
                lt = 0
            if x[32].isdigit():
                mf = float(x[32].strip())*1
            else:
                mf = 0
            if x[33].isdigit():
                ga = float(x[33].strip())*1
            else:
                ga = 0
            if x[34].isdigit():
                fe = float(x[34].strip())*1
            else:
                fe = 0
            if x[35].isdigit():
                be = float(x[35].strip())*1
            else:
                be = 0
            if x[36].isdigit():
                de = float(x[36].strip())*1
            else:
                de = 0
            if x[37].isdigit():
                e1 = float(x[37].strip())*1
            else:
                e1 = 0
            if x[38].isdigit():
                e2 = float(x[38].strip())*1
            else:
                e2 = 0
            if x[39].isdigit():
                e3 = float(x[39].strip())*1
            else:
                e3 = 0
            if x[40].isdigit():
                nv = float(x[40].strip())*1
            else:
                nv = 0
            if x[41].isdigit():
                tr = float(x[41].strip())*1
            else:
                tr = 0
            if x[42].isdigit():
                td = format(float(x[42].strip()*1),'.2f')
            else:
                td = 0
            if x[48].isdigit():
                p1 = float(x[48].strip())*1
            else:
                p1 = 0
            if x[50].isdigit():
                p2 = float(x[50].strip())*1
            else:
                p2 = 0
            if x[62].isdigit():
                la = float(x[62].strip())*1
            else:
                la = 0
            if x[63].isdigit():
                ia = float(x[63].strip())*1
            else:
                ia = 0
            if x[64].isdigit():
                ma = float(x[64].strip())*1
            else:
                ma = 0
                
            #leg = x[69].replace("'", "''")
            if x[65] > '0':
                proploc = x[65].strip()+' '+x[68].strip()+' '+x[66].strip()+' '+x[67].strip()+'                                                         '
            else:
                proploc = ''
            proploc = proploc.strip()
            return [x[0].strip(),x[1].strip(),x[2].strip(),x[3].strip(),x[4].strip(),x[5].strip(),x[6].strip(),x[7].strip()
                    ,x[8].strip(),x[9].strip(),it
                    ,ty,x[12].strip(),x[13].strip(),x[14].strip(),x[15].strip(),x[16].strip(),x[17].strip(),x[18].strip(),x[19].strip(),x[20].strip(),x[21].strip()
                    ,x[22].strip(),x[23].strip(),x[23].strip(),x[23].strip(),x[23].strip(),x[27].strip()
                    ,mc,on,ac
                    ,lt,mf,ga,fe,be
                    ,de,e1,e2,e3,nv
                    ,tr,td,td,td,x[45].strip()
                    ,x[47].strip(),p1,x[49].strip(),p2
                    ,x[53].strip(),x[54].strip(),x[55].strip(),x[56].strip(),proploc,la,ia,ma
                    ,x[65].strip(),x[66].strip(),x[67].strip(),x[68].strip(),x[69].strip()  ]
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
        columns.append('itemnumtaxid varchar(50)')
        columns.append('fullpidnumber varchar(50)')
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
        columnNames = [x.split(' ')[0].upper() for x in columns]
        uniqueColumns = []
        uniqueColumns.append('brwid int identity(1,1)')
        uniqueColumns.append('selectedFlag int')
        uniqueColumns.append('invoiceId int')
        uniqueColumns.append('adtaxId int')
        uniqueColumns.append('taxYear varchar(10)')
        uniqueColumns.append('defaultAddressBlob varchar(max)')
        uniqueColumns.append('balanceDue money')
        uniqueColumns.append('reason varchar(50)')
        uniqueColumns.append('taxrollDetailId int')
        uniqueColumns.append('afullpidnumber varchar(50)')
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
            'propLoc': [['PHYSICALSTREETNUMBER','PHYSICALSTREETDIRECTION' , 'PHYSICALSTREET', 'PHYSICALTOWN'], 'string'],
            'PHYSICALSTREETNUMBER': [['PHYSICALSTREETNUMBER'], 'string'],
            'PHYSICALSTREET': [[ 'PHYSICALSTREET'], 'string'],
            'PHYSICALTOWN': [[ 'PHYSICALTOWN'], 'string'],
            'PHYSICALSTREETDIRECTION': [[ 'PHYSICALSTREETDIRECTION'], 'string'],
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
            return ' '.join(a).strip().replace("'", "")

        taxYear = areYouSure('enter the tax year please', boolean=False)
        if areYouSure('are you sure you want to run with taxYear = %s?' % taxYear):
            print 'Here we go... AAmaster Update...'
            package, fields = self.tpsAamasterGetPackage()
            # testlist = [
            #     '0000-06-02N-01E-0-010-00',
            #     '0000-04-02N-02E-0-011-00',
            # ]
            tally = 0
            if 'rows' in package and len(package['rows']) > 0:
                tallyTotal = len(package['rows'])
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
                    print '.... %s' % tallyTotal
                    q = self.sqlQuery(sqlString, True)
                    if q['code'][0] == 0:
                        tally += 1
                        tallyTotal -= 1
                    else:
                        print 'oops...', q
            print 'ok i sent %s updates' % tally


    def tpsAamasterCheck(self):
        aamasterpath = self.settingsF('checkassessor.sourcepath')
        aamaster = self.settingsF('checkassessor.sourceFile')
        columns, columnNames, uniqueColumns = self.aamasterCheckVariables()
        if(aamaster.lower() != 'aamaster.tps'):
            columnNames.remove('businessname'.upper())
            columnNames.remove('country'.upper())
        if(aamaster.lower() == 'aamaster.tps'):
            columnNames.remove('itemnumtaxid'.upper())
        sqlString = "select \"{fields}\" from {tableName}".format(fields='", "'.join(columnNames), tableName=aamaster.lower().replace('.tps', ''))
#        sqlString = "select * from {tableName}".format(tableName=aamaster.lower().replace('.tps', ''))
        connDatabase = '%s\\%s' % (aamasterpath, aamaster)
        print ' - connDatabase', connDatabase
        print ' - aamasterpath', aamasterpath
        print ' - aamaster', aamaster
        if not aamasterpath:
            print 'missing path to aamaster... fail!'
            return
        package = self.tpsSelect(sqlString, aamaster.lower().replace('.tps', ''), connDatabase=connDatabase)
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
        connectionString = 'APP=%s;DRIVER={%s};SERVER=%s;DATABASE=%s;UID=%s;PWD=%s' % (appName, self.settings['driver'] or 'SQL Server', self.settings['server'], connDatabase, self.settings['uid'], self.settings['password'])
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
