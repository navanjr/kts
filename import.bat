@echo off
REM this script is designed to just import the existing repo into your key environment

@setlocal enableextensions enabledelayedexpansion

pushd c:\client\key\kts

set logFile=..\keyGit.log
del %logFile%

set dbname=%1

set val=
call :getIni ..\keyGit.ini git server
set server=%val%
set serverEsc=%val:\=\\%

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
echo the escaped server is %serverEsc%
echo the dbname is %dbname%
echo the gitPath is %gitPath%
echo the sapass is %sapass%

if "%server%"=="" goto blankserver
if "%dbname%"=="" goto blankdbname
if "%gitPath%"=="" goto blankgitpath
if "%sapass%"=="" goto blanksapass

SET /P runmode=Please Choose ( [T]est connection, [I]mport from repo ): 
IF "%runmode%"=="T" GOTO TestConnection
IF "%runmode%"=="I" GOTO ImportRepo
IF "%runmode%"=="N" GOTO Nate


:TestConnection
sqlcmd -S%server% -d%dbname% -Usa -P%sapass% -Q"select getDate() as current_DateTime"
GOTO:finish

:ImportRepo
dir SqlObjects\ | grep ~1.TXT | grep -vn keyCore | gawk -v cmd="sqlcmd -S%serverEsc% -d%dbname% -Usa -P%sapass% -iSqlObjects\\" "{print cmd $5}" | cmd >> %logFile%
dir SqlObjects\ | grep ~2.TXT | grep -vn keyCore | gawk -v cmd="sqlcmd -S%serverEsc% -d%dbname% -Usa -P%sapass% -iSqlObjects\\" "{print cmd $5}" | cmd >> %logFile%
dir SqlObjects\ | grep ~3.TXT | grep -vn keyCore | gawk -v cmd="sqlcmd -S%serverEsc% -d%dbname% -Usa -P%sapass% -iSqlObjects\\" "{print cmd $5}" | cmd >> %logFile%
dir SqlObjects\ | grep ~4.TXT | grep -vn keyCore | gawk -v cmd="sqlcmd -S%serverEsc% -d%dbname% -Usa -P%sapass% -iSqlObjects\\" "{print cmd $5}" | cmd >> %logFile%
dir SqlObjects\ | grep ~5.TXT | grep -vn keyCore | gawk -v cmd="sqlcmd -S%serverEsc% -d%dbname% -Usa -P%sapass% -iSqlObjects\\" "{print cmd $5}" | cmd >> %logFile%
sqlcmd -S%server% -d%dbname% -Usa -P%sapass% -Q"exec dbo.keyUpdateAll" | grep @code=
if DEFINED dropdll goto dodropdll
GOTO:finish

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
