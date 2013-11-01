@echo off
pushd %~dp0
python kts.py %1 %2 %3
popd
if ERRORLEVEL = 1 GOTO NoPython
GOTO END

:NoPython
echo .
echo  ---------------------------------------------------------
echo    You ?MAY? need to install Active Python...
echo       http://www.activestate.com/activepython/downloads
set /p yesorno="Would you like to open this website?: " %=%
IF /I "%yesorno%"=="Y" call:StartUrl
IF /I "%yesorno%"=="YES" call:StartUrl
GOTO END

:StartUrl
start http://www.activestate.com/activepython/downloads
GOTO END

:END