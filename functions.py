import os
import sys
import pyodbc
import subprocess
import ConfigParser
import ftplib
import shutil


def isnull(what,convertTo=''):
    if what is None:
        return convertTo
    return str(what)

class ktsMenu():
    def __init__(self, database=None):
        self.settings = {}
        self.ftpSettings = {}
        self.defaultFileName = "..\\ktsConfig.ini"
        if database:
            self.dbSettings(database)
        else:
            self.dbSettings(self.configStuff('importDefaults', 'database') or 'kts')

        self.settings['server'] = self.configStuff('importDefaults', 'server') or '.'
        self.settings['uid'] = self.configStuff('importDefaults', 'uid')
        self.settings['password'] = self.configStuff('importDefaults', 'password')

        self.ftpSettingsInit()

        self.conversionSettings = [
            'conversion.mikepath',
            'conversion.mikepathtax',
            'conversion.officialbankcode',
            'conversion.initials',
            'conversion.conversiondate',
        ]

        self.commands = {}
        self.createCommand('exit',['x','exit','q','quit'],'exit ktsMenu',self.command_exit)
        self.createCommand('help',['h','help'],'',self.command_help)
        self.createCommand('testConnection',['test','t','testconnection'],'tests the connection to your sql server',self.command_testConnection)
        self.createCommand('serverSettings',['set'],'modify server settings',self.command_serverSettings)
        self.createCommand('displayMenu',['m','menu','display','displayMenu','refresh'],'redraw menu',self.command_displayMenu)
        self.createCommand('gitCommands',['git'],'run git command',self.command_git)
        self.createCommand('logging',['logging','log','logit'],'modify log settings',self.command_logging)
        self.createCommand('import',['i','import'],'import from repo into your database',self.command_import)
        self.createCommand('diagSQLObjects',['diagsql','diagsqlobjects'],'runs sqlObjects diagnostic',self.diag_sqlObjects)
        self.createCommand('setup',['setup'],'access all the setup options',self.command_initialSetup)
        self.createCommand('importSQLObject',['importsqlobject','importsql'],'import a named sql object from the repo',self.command_importSqlObject)
        self.createCommand('diagnostics',['d','diag','diagnostic','diagnostics'],'access all diagnostic options',self.command_diagnostics)
        self.createCommand('conversion',['c','conv','conversion'],'access all the conversion tools',[self.command_diagnostics,'conversion'])
        self.createCommand('backup',['backup','back'],'back up sql data',self.command_backup)
        self.createCommand('backupNow',['backupNow',],'back up sql data without an "are you sure" prompt',self.command_backupNow)
        self.createCommand('schtasks',['tasks', 'task'],'diaplay all kts tasks',self.scheduledTasks)
        self.createCommand('users',['user','users'],'display or define default users',self.command_users)
        self.createCommand('gitstatus',['status','s'],'preform a git status',[self.command_git,['git','status']])
        self.createCommand('gitpull',['pull','p'],'preform a git log',[self.command_git,['git','pull']])
        self.createCommand('gitpush',['push'],'preform a git push ',self.command_gitpush)
        self.createCommand('ftp',['ftp'],'put a file to the support server',self.ftp_show)
        self.createCommand('gitstatusporcelain',['gsp'],'preform a git status',self.command_importSpecial)

        self.createCommand('settings',['set','settings'],'show all ftp settings',self.ftp_settings,'ftp')
        self.createCommand('put',['put'],'put a file to support',self.ftp_put,'ftp')

        self.createCommand('battery',['b','bat','batt','battery'],'runs light diagnostic battery',self.diagnostic_run,'diagnostics')
        self.createCommand('fix',['f','fix'],'runs diagnostic fix routine, requires the specific diagnostic number',self.diagnostic_fix,'diagnostics')

        self.createCommand('battery',['b','bat','batt','battery'],'runs conversion diagnostic battery',[self.diagnostic_run,'conversion'],'conversion')
        self.createCommand('settings',['settings'],'displays all conversion settings',self.diagnostic_conversionSettings,'conversion')
        self.createCommand('fix',['f','fix'],'runs conversion fix routine requires the specific diagnostic number',[self.diagnostic_fix,'conversion'],'conversion')
        self.createCommand('auto', ['a', 'auto'], 'runs a collection of conversion fix routines', self.diagnostic_auto, 'conversion')
        self.createCommand('aamasterCheck', ['aamasterCheck', ], 'copies some aamaster data into aamasterCheck for kts reports', self.tpsAamasterCheck, 'conversion')
        self.createCommand('importTax', ['importTax', ], 'copies XXXXadtax data into kts for invoicing', self.tpsXXXXadtax, 'conversion')
        self.createCommand('importGSI', ['importGSI', ], 'copies GSI data into aamasterCheck', self.gsiAamasterCheck, 'conversion')

        self.command = []

        self.git = {}
        self.gitVars()

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
        self.settings['defaultUsers'] = self.configStuff(self.settings['database'], 'defaultUsers')

    def gitVars(self):
        try:
            self.git['branch'] = subprocess.check_output("git rev-parse --abbrev-ref HEAD", shell=True)
            self.git['status'] = subprocess.check_output("git status", shell=True)
            self.git['repoVersion'] = subprocess.check_output("cat templates\key~1.TXT|grep ktsTag=", shell=True).replace('@ktsTag=','').replace(';','')
        except subprocess.CalledProcessError:
            self.git['branch'] = ''
            self.git['status'] = ''
            self.git['repoVersion'] = ''
        try:
            self.git['ktsVersion'] = self.sqlQuery("select dbo.readKeyCode(1,'@ktsTag=')")['rows'][0][0]
        except KeyError:
            self.git['ktsVersion'] = 'Unknown'

    def menuShow(self,subMenu):
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

    def scheduledTasks(self):
        taskPrefix = 'kp.%s' % self.settings['database']
        tasks = []
        raw = subprocess.Popen(["schTasks", "/query", "/fo", "csv"], stdout=subprocess.PIPE, shell=True)
        (out, err) = raw.communicate()
        for line in out.split('\n'):
            if taskPrefix in line:
                tasks.append(line.translate(None, '"\\\r').split(','))
        for task in tasks:
            print '     %s - %s   next:%s' % (task[2], task[0], task[1])

    def ftpFiles(self):
        files = {}
        for id, file in enumerate(os.listdir(self.ftpSettings['path'])):
            fileToken = {}
            fileToken['name'] = file
            fileToken['size'] = os.path.getsize('%s/%s' % (self.ftpSettings['path'], file))
            files[id + 1] = fileToken
        return files

    def ftp_show(self):
        files = self.ftpFiles()
        menuName = self.getMenuName(self.command[0],self.commands)
        subMenu = self.commands[menuName]['subMenu']
        for file in files.items():
            print '     %s. %-*s %s mb' % (str(file[0]).rjust(3), 30, file[1]['name'], str(round(file[1]['size'] / 1024.0 / 1024.0, 2)).rjust(10))
        if len(self.command) == 1:
            self.menuShow(subMenu)
        elif len(self.command) > 1:
            self.runMenuFunction(self.command[1],subMenu)

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
            print "back up SQL data...", self.sqlQuery("exec dbo.sqlBackup @returnRows='FALSE'", isProc=True, isBackup=True)['code']

        if bypassConfirmation:
            doit()
        else:
            backupFileName = self.sqlQuery("select path from dbo.paths() where name = 'backup'")['rows'][0][0]
            print "do you wish to backup the DB to..."
            if self.ask("%s?" % backupFileName) in ('yes', 'y'):
                doit()

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

    def createCommand(self,commandName,keywords,description='',function='',parentMenu=None):
        if parentMenu is None:
            self.commands[commandName] = {'keywords':keywords,'description':description,'function':function,'subMenu':{}}
        else:
            self.commands[parentMenu]['subMenu'][commandName] = {'keywords':keywords,'description':description,'function':function}
            
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

    def command_setSetting(self, prefix, defaultValue=None, settingsCRUD=True):
        if not len(self.command) > 1:
            return
        if len(self.command) > 2:
            newValue = self.command[2]
        else:
            if defaultValue:
                print 'leave blank for default value (%s)' % defaultValue
            newValue = raw_input('Enter %s ==> ' % self.command[1]) or defaultValue
        if settingsCRUD:
            self.sqlQuery("exec dbo.settingsCRUD '%s.%s','%s'" % (prefix, self.command[1], newValue), True)
        return newValue
        
    def command_serverSettings(self):
        cmd = self.command[1]
        if len(self.command) < 2:
            return
        if len(self.command) > 2:
            commandArguement = self.command[2]
        else:
            commandArguement = ''
        if cmd in ('db','database'):
            self.dbSettings(commandArguement)
            self.configStuff('importDefaults', 'database', 'PUT', commandArguement)
        elif cmd in ('user','username','uid'):
            self.setVars('uid',commandArguement)
            self.configStuff('importDefaults', 'uid', 'PUT', commandArguement)
        elif cmd in ('pwd','pass','password'):
            self.setVars('password',commandArguement)
            self.configStuff('importDefaults', 'password', 'PUT', commandArguement)
        elif cmd in ('server','location','url'):
            self.setVars('server',commandArguement)
            self.configStuff('importDefaults', 'server', 'PUT', commandArguement)
        elif cmd == 'gitpath':
            self.command_setSetting('git', defaultValue='c:\client\key\kts')
        elif cmd == 'gitcommitter':
            self.command_setSetting('git')
        elif cmd in ('mikepath', 'mikepathtax'):
            self.command_setSetting('conversion', defaultValue='c:\client\dosdata\ctpro\online')
        elif cmd in ('taxyear','officialbankcode','initials','conversiondate'):
            self.command_setSetting('conversion')
        elif cmd in ('ftphost', 'ftpuser', 'ftppassword', 'ftppath'):
            if cmd == 'ftppath':
                newValue = self.command_setSetting('ftp', defaultValue='c:\client\key\sqlBackup')
            else:
                newValue = self.command_setSetting('ftp')
            self.configStuff('ftp', self.command[1].replace('ftp',''), 'PUT', newValue)
            self.ftpSettingsInit()
        elif cmd in ('aamasterpath', 'gsipath'):
            self.command_setSetting('conversion')

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

    def tpsSelect(self, sqlString, dbName, verbose=False, connDatabase=None):
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
            package['rows'] = rows
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
            sqlInsert = "insert adtaxCheck "
            tally = 0
            for id, row in enumerate(package['rows']):
                formatedRow = [str(x).replace("'", "''") for x in row]
                sqlSelect = "select '{values}'".format(values="','".join(formatedRow))
                if self.sqlQuery("%s %s" % (sqlInsert, sqlSelect), True)['code'][0] == 0:
                    tally = tally + 1
            print 'ok i inserted %s records' % tally

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
            zip = row[252:261]
            return [
                itemNumber.strip(),
                name1.strip(),
                name2.strip(),
                mailingInfo.strip(),
                add1.strip(),
                add2.strip(),
                city.strip(),
                state.strip(),
                zip.strip(),
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
            columnNames = ['autonumber','ownername','businessname','address1','address2','address3','city','state','zip1']
            sqlInsert = "insert aamasterCheck ({columns})".format(columns=', '.join(columnNames))
            tally = 0
            for id, row in enumerate(rows):
                formatedRow = [str(x).replace("'", "''") for x in row]
                sqlSelect = "select '{values}'".format(values="','".join(formatedRow))
                if self.sqlQuery("%s %s" % (sqlInsert, sqlSelect), True)['code'][0] == 0:
                    tally = tally + 1
            print 'ok i inserted %s records' % tally

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
                # if id == 2:
                #     break
            print 'ok i inserted %s records' % tally
        print 'dbo.aamasterCheckInitialize...', self.sqlQuery('exec dbo.aamasterCheckInitialize', True)['code']

    def settingsF(self, name, default='unknown'):
        value = self.sqlQuery("select dbo.settingsF('%s','%s')" % (name, default))['rows'][0][0]
        return value

    def sqlQuery(self,sqlString, isProc=False, alternateDatabase=None, isBackup=False):
        connDatabase = alternateDatabase or self.settings['database']
        connectionString = 'DRIVER={SQL Server};SERVER=%s;DATABASE=%s;UID=%s;PWD=%s' % (self.settings['server'],connDatabase,self.settings['uid'],self.settings['password'])
        package = {}
        package['connectionString'] = connectionString
        package['database'] = connDatabase
        package['sqlString'] = sqlString
        try:
            connection = pyodbc.connect(connectionString, autocommit=True)
        except (pyodbc.ProgrammingError, pyodbc.Error):
            package['code'] = [1,'Failed to connect to %s' % connDatabase]

        try:
            cursor = connection.cursor()
        except UnboundLocalError:
            package['code'] = [1, 'Failed to connect to %s' % connDatabase]
            return package

        try:
            cursor.execute(sqlString)
        except pyodbc.ProgrammingError, err:
            package['code'] = [1, 'Error on Execute %s' % err]
            package['rows'] = [('', '')]
            connection.close()
            return package

        if isBackup:
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
