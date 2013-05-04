import os
import sys
import pyodbc
import subprocess

def isnull(what,convertTo=''):
    if what is None:
        return convertTo
    return str(what)

class ktsMenu():
    def __init__(self):
        sysArgs = sys.argv
        self.settings = {}
#TODO be sure to get these setting from ini file
        self.settings['server'] = '.'
        if len(sysArgs) > 1:
            self.settings['database'] = sysArgs[1] or 'bryan'
        else:
            self.settings['database'] = 'kts'
        self.settings['uid'] = 'sa'
        self.settings['password'] = 'America#1'

        self.commands = {}
        self.createCommand('exit',['x','exit','q','quit'],'exit ktsMenu',self.command_exit)
        self.createCommand('help',['h','help'],'',self.command_help)
        self.createCommand('testConnection',['test','t','testConnection'],'tests the connection to your sql server',self.command_testConnection)
        self.createCommand('serverSettings',['set','s'],'modify server settings',self.command_serverSettings)
        self.createCommand('displayMenu',['m','menu','display','displayMenu','refresh'],'redraw menu',self.command_displayMenu)
        self.createCommand('gitCommands',['git'],'run git command',self.command_git)
        self.createCommand('logging',['logging','log','logit'],'modify log settings',self.command_logging)
        self.createCommand('import',['i','import'],'import from repo into your database',self.command_import)
        self.createCommand('diagSQLObjects',['diagsql','diagsqlobjects'],'runs sqlObjects diagnostic',self.diag_sqlObjects)
        self.createCommand('setup',['setup'],'access all the setup options',self.command_initialSetup)
        self.createCommand('importSQLObject',['importsqlobject','importsql'],'import a named sql object from the repo',self.command_importSqlObject)
        self.createCommand('diagnostics',['d','diag','diagnostic','diagnostics'],'access all diagnostic options',self.command_diagnostics)
        self.createCommand('conversion',['c','conv','conversion'],'access all the conversion tools',[self.command_diagnostics,'conversion'])

        self.createCommand('battery',['b','bat','batt','battery'],'runs light diagnostic battery',self.diagnostic_run,'diagnostics')
        self.createCommand('fix',['f','fix'],'runs diagnostic fix routine, requires the specific diagnostic number',self.diagnostic_fix,'diagnostics')

        self.createCommand('battery',['b','bat','batt','battery'],'runs conversion diagnostic battery',[self.diagnostic_run,'conversion'],'conversion')
        self.createCommand('fix',['f','fix'],'runs conversion fix routine requires the specific diagnostic number',[self.diagnostic_fix,'conversion'],'conversion')

        self.command = []

        self.git = {}
        self.gitVars()

    def gitVars(self):
        self.git['branch'] = subprocess.check_output("git rev-parse --abbrev-ref HEAD", shell=True)
        self.git['status'] = subprocess.check_output("git status", shell=True)
        self.git['repoVersion'] = subprocess.check_output("cat templates\key~1.TXT|grep ktsTag=", shell=True).replace('@ktsTag=','').replace(';','')
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

    def diagnostic_fix(self,mode='light'):
        if len(self.command) == 3:
            menuInt = str(self.command[2])
            fixProcName = self.sqlQuery("select fixProc from dbo.diagnosticsBRW('%s',0) where menuInt = %s" % (mode,menuInt))['rows'][0][0]
            sqlcmd = "exec dbo.%s @method = 'fix'" % fixProcName
            print 'running diagnostic fix for %s number %s...' % (mode,menuInt)
            print sqlcmd, self.sqlQuery(sqlcmd,True)['code']

    def diagnostics_show(self,theClass=None):
        sqlcmd = "select display, menuInt from dbo.diagnosticsBRW('%s',0) where tally > 0 order by ord" % theClass
        result = self.sqlQuery(sqlcmd)
        if len(result['rows']) > 1:
            for row in result['rows']:
                print isnull(row[1]).rjust(5),row[0].ljust(30)
        else:
            print 'nothing to report'.rjust(30)
        print

    def diagnostic_run(self,mode='light',show=True):
        print 'run %s diagnostic battery...' % mode, self.sqlQuery("exec dbo.diagnostics @mode='%s', @storeResults='TRUE', @verbose='FALSE'" % mode,True)['code']
        if show:
            self.diagnostics_show(mode)
            
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
            print 'createReasonsToCancel...', self.sqlAlterProc('createReasonsToCancel','Procedure','99')
            print 'paymentTypes...', self.sqlAlterProc('paymentTypes','TableFunction','99')
            print 'journalTypes...', self.sqlAlterProc('journalTypes','TableFunction','99')
            print 'glCreateTables...', self.sqlAlterProc('glCreateTables')
            print 'Run glCreateTables...', self.sqlQuery('exec dbo.glCreateTables',True)['code']
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

        if len(self.command) > 1:
            setupStep = self.command[1]
            if setupStep in ('db','database'):
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

    def sendCommand(self,command):
        self.command = command.split()
        self.runMenuFunction(self.command[0],self.commands)
        return True

    def command_import(self):
        def theMeat():
            print 'ok here goes...'
            self.sqlAlterProc("keySQLObjectDispatcher")
            self.sqlAlterProc("keyUpdateAll",'Procedure',"9999")
            result = self.sqlQuery("exec dbo.keyUpdateAll 'NewMethod','FALSE'",True)
            print 'running dbo.keyUpdateAll', result['code']
            print 'running keySQLObjectCreateAll', self.sqlQuery('exec dbo.keySQLObjectCreateAll',True)['code']
            print 'running dbo.keyTemplateUpdateFromRepo', self.sqlQuery("exec dbo.keyTemplateUpdateFromRepo null",True)['code']
            self.sqlAlterProc("createIndexes","Procedure","99")
            print 'running dbo.createIndexes', self.sqlQuery("exec dbo.createIndexes",True)['code']
            self.sqlAlterProc("createGroups","Procedure","99")
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

    def command_git(self):
        print subprocess.check_output(' '.join(self.command), shell=True)

    def command_testConnection(self,display=True):
        result = {}
        gitDict = {}
        rows = self.sqlQuery("select settingName, settingValue from settings where dbo.splitF(settingName,'.',1) in ('git','logging')")['rows']
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

    def command_gitSetting(self):
        if not len(self.command) > 1:
            return
        if len(self.command) > 2:
            newValue = self.command[2]
        else:
            newValue = raw_input('Enter %s ==> ' % self.command[1])
        self.sqlQuery("exec dbo.settingsCRUD 'git.%s','%s'" % (self.command[1],newValue),True)
        
    def command_serverSettings(self):
        if len(self.command) > 2:
            commandArguement = self.command[2]
        else:
            commandArguement = ''
        if self.command[1] in ('db','database'):
            self.setVars('database',commandArguement)
        elif self.command[1] in ('user','username','uid'):
            self.setVars('uid',commandArguement)
        elif self.command[1] in ('server','location','url'):
            self.setVars('server',commandArguement)
        elif self.command[1] in ('gitpath','gitcommitter','mikepath'):
            self.command_gitSetting()

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

    def sqlQuery(self,sqlString,isProc=False,alternateDatabase=None):
        connDatabase = alternateDatabase or self.settings['database']
        connectionString = 'DRIVER={SQL Server};SERVER=%s;DATABASE=%s;UID=%s;PWD=%s' % (self.settings['server'],connDatabase,self.settings['uid'],self.settings['password'])
        package = {}
        package['connectionString'] = connectionString
        package['database'] = connDatabase
        package['sqlString'] = sqlString
        try:
            connection = pyodbc.connect(connectionString, autocommit=True)
        except pyodbc.ProgrammingError:
            package['code'] = [1,'Failed to connect to %s' % connDatabase]
        cursor = connection.cursor()
        try:
            cursor.execute(sqlString)
        except pyodbc.ProgrammingError:
            package['code'] = [1,'execution failed']
            package['rows'] = [('','')]
            return package

        if isProc:
            package['code'] = [0,'ok']
            package['rows'] = [('','')]
        else:
            try:
                rows = cursor.fetchall()
                package['code'] = [0,'ok']
                package['rows'] = rows
            except pyodbc.ProgrammingError:
                package['code'] = [1,'execution failed']
                package['rows'] = [('','')]
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


