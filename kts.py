from functions import *

sysArgs = sys.argv
autoArgs = ['ftp', 'conv', 'backupNow', 'api', 'compress','import']

if len(sysArgs) > 1 and sysArgs[1] not in autoArgs:
    database = sysArgs[1]
else:
    database = None

menu = ktsMenu(database)

if len(sysArgs) == 2 and sysArgs[1] in autoArgs:
    menu.sendCommand(sysArgs[1])

elif len(sysArgs) > 2 and sysArgs[1] in autoArgs:
    if sysArgs[1] == 'ftp':
        menu.ftp_put(sysArgs[2])
    elif sysArgs[1] == 'conv' and sysArgs[2] == 'importTax':
        menu.tpsXXXXadtax()
    elif sysArgs[1] == 'conv' and sysArgs[2] == 'importTaxLv':
        menu.tpsXXXXtxlv()
    elif sysArgs[1] == 'conv' and sysArgs[2] == 'importTaxFee':
        menu.tpsXXXXfee()
    elif sysArgs[1] == 'conv' and sysArgs[2] == 'importTaxNote':
        menu.tpsXXXXnote()
    elif sysArgs[1] == 'conv' and sysArgs[2] == 'importGSITax':
        menu.gsiTaxroll()
    elif sysArgs[1] == 'conv' and sysArgs[2] == 'importDBF':
        menu.sendCommand(' '.join(sysArgs[1:]))
    elif sysArgs[1] == 'conv' and sysArgs[2] == 'aamasterCheck':
        menu.sendCommand(' '.join(sysArgs[1:]))
    elif sysArgs[1] in ('api', 'compress'):
        menu.sendCommand(' '.join(sysArgs[1:]))

else:
    menu.display()
    continueSwitch = True

    while True:
        print
        command = raw_input('      your wish ==> ')
        continueSwitch = menu.sendCommand(command)
        if continueSwitch != True:
            break
