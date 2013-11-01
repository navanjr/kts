import binascii
import cPickle as pickle
import threading
from datetime import datetime
from general import *
import dbf

class commands():
    def __init__(self):
        self.cmd = {}

    def addCommand(self, commandName, keywordArray, description='', function='', subMenu=None):
        self.cmd[commandName] = {
            'keywords': keywordArray,
            'description': description,
            'function': function,
            'subMenu': subMenu
        }

    def get(self, keyword):
        for item in self.cmd.items():
            if keyword in item[1]['keywords']:
                return item[1]

    def run(self, keyword):
        if self.get(keyword):
            self.get(keyword)['function']()

    def show(self):
        print
        for key, value in self.cmd.items():
            print key.rjust(20), '-', value['description']


class pickler():
    def __init__(self, foxData, workingTable, verbose=True):
        self.key = foxData['tables'][workingTable]['key']
        self.countyName = foxData['countyName'] or 'unknown'
        self.map = foxData['tables'][workingTable]['map']
        self.picklePath = foxData['picklePath'] or '..'
        self.apiSettings = foxData['apiSettings']
        self.dbfName = foxData['tables'][workingTable]['dbfName']
        self.verbose = verbose
        self.blob = {}
        self.years = foxData['yearsToProcess'] or []
        self.pathToDBFs = foxData['pathToDBFs']

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        del self.blob

    def say(self, *what):
        say(what, verbose=self.verbose)

    def save(self):
        pickleFile = '%s\\kps_%s_%s.pk' % (self.picklePath, self.countyName, self.key)
        self.say('...Pickling Data...(%s)' % pickleFile)
        file = open(pickleFile, 'wb')
        try:
            pickle.dump(self.blob, file, pickle.HIGHEST_PROTOCOL)
        except pickle.PicklingError, e:
            self.say('Error during pickle...', e)

    def load(self):
        self.say('...opening data...(%s)' % self.key)
        try:
            file = open('%s\\kps_%s_%s.pk' % (self.picklePath, self.countyName, self.key), 'rb')
        except IOError:
            self.say('pickle not found...')
            self.blob = {'data': {}, 'info': {}}
            return
        try:
            self.blob = pickle.load(file)
        except TypeError, e:
            self.say('seems to be a problem with the pickled data...', e)
            self.blob = {'data': {}, 'info': {}}

    def foxFetch(self):
        key = self.key
        map = self.map
        if not self.pathToDBFs:
            say('sorry, you need to specify the path to the DBFs.')
            return
        if key:
            filename = "%s\\%s" % (self.pathToDBFs, self.dbfName)
            self.say('ok, processing %s - %s' % (key, filename))
            dbfTable = dbf.Table(filename)
            dbfTable.use_deleted = False
            dbfTable.ignore_memos = True
            dbfTable.open()
            self.blob['info'] = str(dbfTable)
            self.blob['data'] = {}
            print '     please wait while we are creating an index for %s...' % key
            scratch = dbfTable.create_index(lambda rec: rec.taxyear+rec.itm_nbr)
            print '      ...mapping data...'
            for id, record in enumerate(scratch):
                if record['taxyear'] in [str(y) for y in self.years] or not self.years:
                    mappedRow = foxMapper(record, map, self.apiSettings)
                    if mappedRow['tax_roll_link'] > '  0':
                        self.blob['data'][mappedRow['tax_roll_link']] = {
                            'id': id,
                            'updated': 0,
                            'apiRow': mappedRow,
                        }
            return True
        else:
            return False

    def fetchAndSave(self):
        self.foxFetch()
        self.save()

    def get(self, key=None):
        self.load()
        if key:
            return self.blob[key]
        else:
            return self.blob


class kps():
    def __init__(self, parent=None, apiSettings=None, picklePath=None, yearsToProcess=None, pathToDBFs=None, countyName=None):
        self.parent_ = parent
        self.apiSettings = apiSettings
        self.command = []
        self.foxData = {}
        self.workingTable = None
        self.batchSize = 100
        self.c = commands()
        self.sendLoop = False
        self.c.addCommand('initialize', ['initialize', 'init', 'i'], 'open foxdata and index', self.initialize)
        self.c.addCommand('info', ['info'], 'display the stats', self.info)
        self.c.addCommand('structure', ['struct', 'structure'], 'display the dbf structure', self.displayStructure)
        self.c.addCommand('sample', ['sample', 'samp'], 'show a sample of the api JSON data', self.displaySample)
        self.c.addCommand('key', ['key'], 'show api JSON data for given key', self.displayKey)
        self.c.addCommand('send', ['send'], 'send the kps data to the api', self.send)
        self.c.addCommand('results', ['result', 'results', 'r'], 'display the results', self.showResults)
        self.c.addCommand('help', ['help', 'h'], 'get kps help', self.help)
        self.c.addCommand('batchSize', ['batch', 'b'], 'set kps batch size', self.setBatchSize)
        self.c.addCommand('reset', ['reset'], 'reset updated flag on table', self.reset)
        self.c.addCommand('test', ['test', 't'], 'test', self.test)
        self.c.addCommand('setTable', ['set', 'setTable', 'table'], 'set working table', self.setTable)
        self.c.addCommand('maxUpdated', ['max', 'maxUpdated', 'maxupdated'], 'get max updated from the API', self.maxUpdated)
        self.c.addCommand('markUpdated', ['mark', 'markUpdated', 'markupdated'], 'mark max updated from the API', self.markUpdated)

        self.foxData['countyName'] = countyName
        self.foxData['pathToDBFs'] = pathToDBFs
        self.foxData['yearsToProcess'] = yearsToProcess
        self.foxData['picklePath'] = picklePath
        self.foxData['apiSettings'] = self.apiSettings

        self.foxData['tables'] = {}
        self.foxData['tables']['taxroll'] = {
            'process': True,
            'key': 'taxroll',
            'dbfName': 'taxroll.dbf',
            'resource': 'v2/treasurer/tax_rolls.json',
            'map': [
                ['tax_year', 'taxyear'],
                ['tax_roll_link', ['concatenate', ['taxyear', 'itm_nbr'], [4, 6]]],
                ['tax_type', 'typ'],
                ['owner', 'name'],
                ['owner_address1', 'addl1'],
                ['owner_address2', 'addl2'],
                ['owner_city', 'city'],
                ['owner_state', 'state'],
                ['owner_postal', 'zip_1'],
                ['parcel', 'parcel'],
                # ['addition', ''],
                # ['block', ''],
                # ['lot', ''],
                ['acres', 'acres'],
                ['property_address1', 'proploc'],
                # ['property_address2', ''],
                # ['property_city', ''],
                # ['property_state', ''],
                # ['property_postal', ''],
                # ['assessed_gross', ''],
                ['assessed_net', 'net_assd'],
                ['assessed_improvements', 'g_imp'],
                ['assessed_mobile_home', 'mobile_hm'],
                ['assessed_exemption', 'exemp'],
                ['millage_rate', 'levy'],
                ['school_district', ['joinWithSpace', ['c_schn', 'c_cityc']]],
                ['item_number', 'itm_nbr'],
                ['legal_description', ['joinWithSpace', ['leg_l1', 'leg_l2', 'leg_l3', 'leg_l4', 'leg_l5', 'leg_l6']]],
                # ['tsvector', ''],
                ['assessed_property', 'g_per'],
                # ['assessed_miscellaneous', ''],
                ['mortgage_code', 'treamort'],
            ],
            'stats': {},
            'info': '',
            'results': {},
        }

        self.foxData['tables']['invoice'] = {
            'process': True,
            'key': 'invoice',
            'dbfName': 'taxroll.dbf',
            'resource': 'v2/treasurer/invoices.json',
            'map': [
                ['tax_year', 'taxyear'],
                ['tax_roll_link', ['concatenate', ['taxyear', 'itm_nbr'], [4, 6]]],
                ['invoice_type', 'typ'],
                ['owner', 'name'],
                ['parcel', 'parcel'],
                ['item_number', 'itm_nbr'],
                # ['posted_date', ''], not sure what to use here on taxrollInvoices
                ['invoice_amount', 'tax_due'],
                ['invoice_link', ['concatenate', ['taxyear', 'itm_nbr'], [4, 6]]],
            ],
            'stats': {},
            'info': '',
            'results': {},
        }

        self.foxData['tables']['receipt'] = {
            'process': True,
            'key': 'receipt',
            'dbfName': 'receipt.dbf',
            'resource': 'v2/treasurer/receipts.json',
            'map': [
                ['tax_roll_link', ['concatenate', ['taxyear', 'itm_nbr'], [4, 6]]],
                ['invoice_link', ['concatenate', ['taxyear', 'itm_nbr'], [4, 6]]],
                ['receipt_link', ['concatenate', ['nbr', 'key_suf'], [8, 2]]],
                ['paid_date', 'datepaid'],
                ['receipt_number', 'nbr'],
                ['paid_fees', 'feespaid'],
                ['paid_penalities', 'penpaid'],
                # ['paid_total', ['math.add', ['feespaid', 'penpaid', 'taxpaid', 'mailpaid', 'lienpaid', 'advpaid', 'mowpaid', 'otherpaid']]],
                ['paid_total', 'taxpaid'],
             # 15) recby C(15)
                ['paid_by', 'paidby'],
             # 17) protestamt N(11,2)
             # 18) pkey C(8)
             # 19) rc C(1)
             # 20) pbnam C(30)
             # 21) r_memo M
            ],
            'stats': {},
            'info': '',
            'results': {},
        }

    def maxUpdated(self):
        pass

    def markUpdated(self, maxKey=None):
        def core(data, maxKey, change):
            tally = 0
            for row in sorted(data.items()):
                if row[1]['updated'] == 0 and row[0] <= maxKey:
                    tally += 1
                    if change:
                        row[1]['updated'] = 1
            return tally

        if self.workingTable:
            maxKey = areYouSure('enter key...', boolean=False)
            with pickler(self.foxData, self.workingTable) as p:
                pTable = p.get()
                data = pTable['data']
                if areYouSure('update %s keys as updated?' % core(data, maxKey, False)):
                    print 'updated keys...(%s)' % core(data, maxKey, True)
                    p.save()
                    self.gatherStats()
                    self.info()

    def setBatchSize(self):
        cmd = self.command
        if len(cmd) == 1:
            newBatchSize = areYouSure('please enter the new batch size')
            self.batchSize = int(newBatchSize)
        elif len(cmd) > 1:
            self.batchSize = int(cmd[1])
            print 'ok, batch size is now %s' % self.batchSize

    def help(self):
        self.c.show()

    def menu(self):
        while True:
            print
            if self.sendLoop:
                self.command = raw_input('').split()
            else:
                self.command = raw_input('      your wish =(kps.%s)=> ' % self.workingTable or '?').split()
            if len(self.command) > 0:
                if self.command[0] in ['exit', 'x']:
                    break
                self.c.run(self.command[0])
            elif self.command < '  0':
                self.sendLoop = False

    def tableList(self, returnAllTables=False):
        if self.workingTable and not returnAllTables:
            return [self.workingTable]
        else:
            return [table for table in self.foxData['tables']]

    def setTable(self):
        valid = []
        tables = [table for table in self.tableList(True)]
        print '      %s) %s' % (0, 'None')
        for i, table in enumerate(tables):
            print '      %s) %s' % (i + 1, table)
            valid.append(str(i + 1))
        youChose = areYouSure('Please choose a table', boolean=False)
        if youChose in valid:
            self.workingTable = tables[int(youChose) - 1]
            self.gatherStats()
        elif youChose == '0':
            self.workingTable = None

    def reset(self):
        if areYouSure():
            for table in self.tableList():
                with pickler(self.foxData, table) as p:
                    data = p.get('data')
                    for key in data:
                        data[key]['updated'] = 0
                    self.gatherStats(data)
                    p.save()
                    self.info()

    def initialize(self):
        for table in self.tableList():
            with pickler(self.foxData, table) as p:
                p.fetchAndSave()
        self.gatherStats()

    def info(self, showResults=False, tableName=None):
        print
        for table in self.tableList():
            tableInfo = self.foxData['tables'][table]
            print '      %s' % table,
            print ' stats: %s' % tableInfo['stats']
            if showResults:
                print ' results...'
                for key, value in tableInfo['results'].items():
                    print key, value
        if tableName:
            t = self.foxData['tables'][tableName]
            print t['info']
            for key, value in t['data'].items()[0:1]:
                print key, value
                for field, value in value['apiRow'].items():
                    print '   %s: %s' % (field, value)

    def displayStructure(self):
        print
        for table in self.tableList():
            info = self.foxData['tables'][table]
            print info['info']

    def displaySample(self):
        if self.workingTable:
            print
            with pickler(self.foxData, self.workingTable) as p:
                for row in sorted(p.get('data').items())[0:10]:
                    print row

    def displayKey(self):
        if len(self.command) == 2 and self.workingTable:
            key = self.command[1]
            with pickler(self.foxData, self.workingTable) as p:
                try:
                    apiRow = p.get('data')[key]
                    print
                    print apiRow
                    print
                    for key, value in apiRow['apiRow'].items():
                        print key, value
                except KeyError, e:
                    print 'sorry i could not find this key: %s' % key, e

    def gatherStats(self, data=None):
        def core(data, table, info=None):
            maxKey = ''
            for i in sorted(data.items()):
                if i[1]['updated'] == 1:
                    maxKey = i[0]
            st = self.foxData['tables'][table]
            st['stats'] = {
                'count': len(data),
                'updated': sum(1 for i in data.items() if i[1]['updated'] == 1),
                'maxKey': maxKey
            }
            st['stats']['stale'] = st['stats']['count'] - st['stats']['updated']
            if info:
                st['info'] = info

        if data and self.workingTable:
            core(data, self.workingTable)
        else:
            for table in self.tableList():
                with pickler(self.foxData, table) as p:
                    pickleGet = p.get()
                    core(pickleGet['data'], table, pickleGet['info'])

    def showResults(self):
        self.info(showResults=True)

    def send(self):
        t = threading.Thread(name='api', target=self.sendThread)
        t.setDaemon(True)
        t.start()

    def sendThread(self):
        passedKeys = None
        if not self.workingTable:
            return
        if len(self.command) > 1:
            passedKeys = self.command[1:]

        self.sendLoop = True
        with pickler(self.foxData, self.workingTable) as p:
            pTable = p.get()
            data = pTable['data']
            self.gatherStats(data)
            wtObj = self.foxData['tables'][self.workingTable]
            stale = wtObj['stats']['stale']
            if stale < 1 and not passedKeys:
                print '      no data in %s.  you will need to initialze or reset' % self.workingTable
            else:
                step, seconds = self.batchSize, 0
                if passedKeys:
                    i = 1
                else:
                    i = stale / float(step)
                while i > 0:
                    if not self.sendLoop:
                        break
                    try:
                        if passedKeys:
                            nKeys = passedKeys
                        else:
                            nKeys = self.nextXKeys(data)
                        minutes = (i * seconds)/60
                        print '      %s  Min:{0:.{1}f} ---> '.format(minutes,2) % (i),
                        sendSuccess, wtObj['results'][i] = self.sendCore(data, nKeys, wtObj)
                        rt = wtObj['results'][i]
                        if sendSuccess:
                            print rt
                            # update the results
                            for key in nKeys:
                                data[key]['updated'] = 1
                        else:
                            print 'failed...', rt
                        seconds = rt['seconds']
                        i = i - 1
                        if passedKeys:
                            break
                    except KeyboardInterrupt:
                        break
                self.gatherStats(data)
                p.save()
                self.info()

    def test(self):
        self.gatherStats()

    def nextXKeys(self, data, quantity=None):
        quantity = quantity or self.batchSize
        keys = []
        for row in sorted(data.items()):
            if not row[1]['updated'] == 1:
                keys.append(row[0])
            if len(keys) >= quantity:
                break
        return keys

    def sendCore(self, data, keys, wtObj):
        returnObj = {}
        startTime = datetime.now()
        if len(data) < 1:
            return
        dump = []
        for key in keys:
            dump.append(data[key]['apiRow'])
        apiSuccess, returnObj['apiResult'] = apiCall(self.apiSettings['host'], self.apiSettings['key'], resource=wtObj['resource'], data=dump)
        endTime = datetime.now()
        tdelta = endTime - startTime
        seconds = tdelta.total_seconds()
        returnObj['seconds'] = seconds
        if apiSuccess:
            if returnObj['apiResult']['failed'] > 0:
                return False, returnObj
            elif returnObj['apiResult']['updated'] + returnObj['apiResult']['created'] == len(keys):
                return True, returnObj
        else:
            return False, returnObj


def foxMapper(record, map, apiSettings):
    def mapHelper(mapItem, record):
        def clean(dirtArray, stripChar=None):
            if not type(dirtArray) == list:
                dirtArray = [dirtArray]
            for dirt in dirtArray:
                try:
                    if type(dirt) in [unicode]:
                        if stripChar:
                            return dirt.encode("ascii").replace(stripChar, '').strip()
                        else:
                            return dirt.encode("ascii").strip()
                    else:
                        return dirt
                except AttributeError, e:
                    print 'type: %s' % type(dirt), e

        key = mapItem[0]
        value = ''
        if type(mapItem[1]) is list:
            verb = mapItem[1][0]
            arguments = mapItem[1][1:]
            if verb in ['cat', 'concat', 'concatenate']:
                if len(arguments) > 2:
                    for i, y in enumerate(arguments[0]):
                        value += clean(record[y]).replace('.', '').zfill(arguments[1][i])
                else:
                    for y in arguments[0]:
                        value += clean(record[y]).replace('.', '')
            if verb in ['joinWithSpace']:
                vArray = []
                for y in arguments[0]:
                    if y in ('leg_l1', 'leg_l2', 'leg_l3', 'leg_l4', 'leg_l5', 'leg_l6'):
                        try:
                            vArray.append(clean(record[y]))
                        except UnicodeDecodeError, e:
                            print 'Unicode Decode Error... ', e
                            print 'COLUMN: ', y, record['taxyear'], record['itm_nbr']
                            testUtf8 = record[y].encode("utf-8")
                            print "utf-8: ", testUtf8
                    else:
                        vArray.append(clean(record[y]))
                value = ' '.join(vArray)
            elif 'math' in verb:
                if 'add' in verb:
                    for y in arguments:
                        if value < '  0':
                            value = '0'
                        if y > '  0':
                            value = 10.00
                            # value = eval('%s + %s' %(value, record[y]))
        else:
            value = clean(record[mapItem[1]])
        return key, value

    o = {}
    o['site_id'] = apiSettings['siteId']
    o['origin'] = apiSettings['origin']
    for x in map:
        apiField, value = mapHelper(x, record)
        o[apiField] = value
    return o