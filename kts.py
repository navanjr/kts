from functions import *

menu = ktsMenu()
menu.display()
continueSwitch = True

while True:
    print
    command = raw_input('      your wish ==> ').lower()
    continueSwitch = menu.sendCommand(command)
    if continueSwitch != True:
        break
