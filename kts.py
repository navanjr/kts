from functions import *

sysArgs = sys.argv

if len(sysArgs) > 1 and sysArgs[1] not in ('ftp', 'conv'):
    database = sysArgs[1]
else:
    database = None

menu = ktsMenu(database)

if len(sysArgs) > 2 and sysArgs[1] in ('ftp', 'conv'):
    if sysArgs[1] == 'ftp':
        menu.ftp_put(sysArgs[2])
    elif sysArgs[1] == 'conv' and sysArgs[2] == 'importTax':
        menu.tpsXXXXadtax()
else:
    menu.display()
    continueSwitch = True

    while True:
        print
        command = raw_input('      your wish ==> ')
        continueSwitch = menu.sendCommand(command)
        if continueSwitch != True:
            break
