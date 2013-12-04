__author__ = 'nate'
import dbf


class dbfClass():
    def __init__(self, originalFile, tableName, fieldsArray=None):
        self.data = {}
        self.data['structure'] = []
        self.data['rows'] = []
        self.data['insertRows'] = []
        self.data['tableName'] = "temp_%s" % tableName
        self.data['originalFile'] = originalFile
        self.data['fieldsArray'] = fieldsArray

    def load(self):
        d = self.data
        dbfTable = dbf.Table(d['originalFile'])
        dbfTable.use_deleted = False
        dbfTable.ignore_memos = True
        dbfTable.open()

        s = d['structure']

        # if we can read the structure
        if len(dbfTable.structure()) > 0:
            for column in dbfTable.structure():
                if self.data['fieldsArray']:
                    if not self.data['fieldsArray'][0] == 'None':
                        if column.split()[0] in self.data['fieldsArray']:
                            print "found %s in fieldsArray" % column.split()[0], column
                            s.append([column.split()[0], column.split()[1].replace("C", "varchar").replace("N", "numeric")])
                    else:
                        s.append([column.split()[0], column.split()[1].replace("C", "varchar").replace("N", "numeric")])
                else:
                    s.append([column.split()[0], column.split()[1].replace("C", "varchar").replace("N", "numeric")])
        else:
            for column in self.data['fieldsArray']:
                s.append([column, "varchar(max)"])

        r = d['rows']
        ir = d['insertRows']
        nColumns = []
        vColumns = []
        for column in s:
            if 'varchar' in column[1]:
                vColumns.append(column[0])
            else:
                nColumns.append(column[0])

        for row in dbfTable:
            obj = {}
            nValues = []
            vValues = []
            for column in s:
                obj[column[0]] = row[column[0]]
                if 'varchar' in column[1]:
                    vValues.append(row[column[0]] or "".replace("'", ""))
                else:
                    nValues.append(str(row[column[0]] or 0))
            r.append(obj)
            sql = "insert %s ({nColumns},{vColumns}) select {nValues},'{vValues}'" % d['tableName']
            sql = sql.format(
                nColumns=",".join(nColumns),
                vColumns=",".join(vColumns),
                nValues=",".join(nValues),
                vValues="','".join(vValues)
            )
            sql = sql.replace("(,", "(")
            sql = sql.replace("select ,", "select ")
            ir.append(sql)

        tb = d['tableName']
        st = ["%s %s" % (x[0], x[1]) for x in s]
        sql = "if exists(select * from dbo.sysobjects" \
              " where id = object_id(N'[dbo].[%s]') and OBJECTPROPERTY(id, N'IsTable') = 1)" \
              " drop table %s;create table %s({columns})" % (tb, tb, tb)
        self.data['dropAndCreateTableSQL'] = sql.format(columns=", ".join(st))
        # for record in dbfTable:
        #     print type(record)
        # print '     please wait while we are creating an index for %s...' % key
        # scratch = dbfTable.all()
        # print scratch
        # print '      ...mapping data...'
        # for id, record in enumerate(scratch):
        #     if record['taxyear'] in [str(y) for y in self.years] or not self.years:
        #         mappedRow = foxMapper(record, map, self.apiSettings)
        #         if mappedRow['tax_roll_link'] > '  0':
        #             self.blob['data'][mappedRow['tax_roll_link']] = {
        #                 'id': id,
        #                 'updated': 0,
        #                 'apiRow': mappedRow,
        #             }
        # return True

    def get(self):
        return self.data

    def save(self):
        pass