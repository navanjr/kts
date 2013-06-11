from functions import *
f = open('c:\myfile.txt','w')
f.write('hi there\n')

sysArgs = sys.argv

if len(sysArgs) > 1 and sysArgs[1] not in ('ftp',):
    database = sysArgs[1]
else:
    database = None

menu = ktsMenu(database)

if len(sysArgs) > 2 and sysArgs[1] in ('ftp',):
    menu.ftp_put(sysArgs[2])
else:
    menu.display()
    continueSwitch = True

    while True:
        print
        command = raw_input('      your wish ==> ')
        continueSwitch = menu.sendCommand(command)
        if continueSwitch != True:
            break
