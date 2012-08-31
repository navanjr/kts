@echo off
REM this script is designed to just import the existing repo into your key environment

@setlocal enableextensions enabledelayedexpansion

pushd c:\client\key\kts

REM set file=..\keyGit.ini
REM set area=[git]
REM set key=path

set dbname=%1

set val=
call :getIni ..\keyGit.ini git server
set server=%val%

set val=
call :getIni ..\keyGit.ini git path
set gitPath=%val%

set val=
call :getIni ..\keyGit.ini git saPass
set sapass=%val%

set val=
call :getIni ..\keyGit.ini git dropdll
set dropdll=%val%

echo the server is %server%
echo the dbname is %dbname%
echo the gitPath is %gitPath%
echo the sapass is %sapass%

if "%server%"=="" goto blankserver
if "%dbname%"=="" goto blankdbname
if "%gitPath%"=="" goto blankgitpath
if "%sapass%"=="" goto blanksapass

sqlcmd -S%server% -d%dbname% -U%dbname% -Usa -P%sapass% -Q"exec dbo.keyUpdateAll" | grep @code=

if DEFINED dropdll goto dodropdll


:finish
echo finished
popd
endlocal
GOTO:EOF


:dodropdll
del %dropdll%
echo I dropped it like it was hot
GOTO:finish

:blankdbname
echo Sorry, you gotta pass me a dbname
GOTO:finish
:blankserver
echo Sorry, your missing a server name (check your ini)
GOTO:finish
:blankgitpath
echo Sorry, your missing a path to your git repo (check your ini)
GOTO:finish
:blanksapass
echo Sorry, your missing an sa password (check your ini)
GOTO:finish


:getIni
set file=%1
set area=[%2]
set key=%3
set currarea=
for /f "delims=" %%a in (!file!) do (
    set ln=%%a
    if "x!ln:~0,1!"=="x[" (
        set currarea=!ln!
    ) else (
        for /f "tokens=1,2 delims==" %%b in ("!ln!") do (
            set currkey=%%b
            set currval=%%c
            if "x!area!"=="x!currarea!" if "x!key!"=="x!currkey!" (
                set val=!currval!
            )
        )
    )
)
GOTO:EOF
