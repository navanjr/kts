@echo off
REM this script is designed to just import the existing repo into your key environment

@setlocal enableextensions enabledelayedexpansion

pushd c:\client\key\kts

set logFile=..\keyGit.log
del %logFileim	%

set dbname=%1

set val=
call :getIni ..\keyGit.ini git server
set server=%val%
set serverEsc=%val:\=\\%

set val=
call :getIni ..\keyGit.ini git path
set gitPath=%val%

set val=
call :getIni ..\keyGit.ini git user
set user=%val%

set val=
call :getIni ..\keyGit.ini git pass
set pass=%val%

set val=
call :getIni ..\keyGit.ini git dropdll
set dropdll=%val%

echo the server is %server%
echo the escaped server is %serverEsc%
echo the dbname is %dbname%
echo the gitPath is %gitPath%
echo the user is %user%
echo the pass is %pass%

if "%server%"=="" goto blankserver
if "%dbname%"=="" goto blankdbname
if "%gitPath%"=="" goto blankgitpath
if "%user%"=="" goto blankuser
if "%pass%"=="" goto blankpass

echo ==============================
echo     Options
echo ==============================
echo   [T]est Connection
echo   [I]mport from repo
echo   [G]it Committer
echo   [S]erver's Path to the Repo
echo ------------------------------
SET /P runmode=Please Choose:
IF /I "%runmode%"=="T" GOTO TestConnection
IF /I "%runmode%"=="I" GOTO ImportRepo
IF /I "%runmode%"=="G" GOTO SetGitCommitterQ
IF /I "%runmode%"=="S" GOTO SetServerPath
IF /I "%runmode%"=="N" GOTO Nate
GOTO:finish

:SetGitCommitterQ
SET /P qanswer=set gitCommitter? ( [E]nable / [D]isable )
IF /I "%qanswer%"=="E" call :SetGitCommitter TRUE
IF /I "%qanswer%"=="D" call :SetGitCommitter FALSE
GOTO:finish

:SetServerPath
SET /P newPath=Enter the Path to the Repo from the Server:
sqlcmd -S%server% -d%dbname% -U%user% -P%pass% -Q"update object set b13='@gitPath=%newPath%;' where typ=0 and link1=-1"
echo @gitPath=%newPath%
GOTO:finish

:SetGitCommitter
set gcValue=%1
sqlcmd -S%server% -d%dbname% -U%user% -P%pass% -Q"update object set b14='@gitCommitter=%gcValue%;' where typ=0 and link1=-1"
echo set @gitCommitter=%gcValue%
GOTO:finish

:TestConnection
sqlcmd -S%server% -d%dbname% -U%user% -P%pass% -Q"select b13 as gitPath, b14 as gitCommitter from Object where Link1 = -1 and TYP = 0"
GOTO:finish

:dropObjects
dir SqlObjects\ /b | grep ~1.TXT | sed "s/~/ /g" | gawk -v cmd="sqlcmd -S%serverEsc% -d%dbname% -U%user% -P%pass% -Q\"" -v cmde="\"" -v c1="drop " -v c2=" dbo." "{print cmd c1 $2 c2 $1 cmde}" | sed "s/ScalarFunction/Function/" | sed "s/TableFunction/Function/"
GOTO:finish

:ImportRepo
dir SqlObjects\ | grep ~1.TXT | grep -vn keyCore | gawk -v cmd="sqlcmd -S%serverEsc% -d%dbname% -U%user% -P%pass% -iSqlObjects\\" "{print cmd $5}" | cmd >> %logFile%
dir SqlObjects\ /b | grep ~1.TXT | sed "s/~/ /g" | gawk -v cmd="sqlcmd -S%serverEsc% -d%dbname% -U%user% -P%pass% -Q\"" -v cmde="\"" -v c1="drop " -v c2=" dbo." "{print cmd c1 $2 c2 $1 cmde}" | sed "s/ScalarFunction/Function/" | sed "s/TableFunction/Function/"
dir SqlObjects\ | grep ~2.TXT | grep -vn keyCore | gawk -v cmd="sqlcmd -S%serverEsc% -d%dbname% -U%user% -P%pass% -iSqlObjects\\" "{print cmd $5}" | cmd >> %logFile%
dir SqlObjects\ /b | grep ~2.TXT | sed "s/~/ /g" | gawk -v cmd="sqlcmd -S%serverEsc% -d%dbname% -U%user% -P%pass% -Q\"" -v cmde="\"" -v c1="drop " -v c2=" dbo." "{print cmd c1 $2 c2 $1 cmde}" | sed "s/ScalarFunction/Function/" | sed "s/TableFunction/Function/"
dir SqlObjects\ | grep ~3.TXT | grep -vn keyCore | gawk -v cmd="sqlcmd -S%serverEsc% -d%dbname% -U%user% -P%pass% -iSqlObjects\\" "{print cmd $5}" | cmd >> %logFile%
dir SqlObjects\ /b | grep ~3.TXT | sed "s/~/ /g" | gawk -v cmd="sqlcmd -S%serverEsc% -d%dbname% -U%user% -P%pass% -Q\"" -v cmde="\"" -v c1="drop " -v c2=" dbo." "{print cmd c1 $2 c2 $1 cmde}" | sed "s/ScalarFunction/Function/" | sed "s/TableFunction/Function/"
dir SqlObjects\ | grep ~4.TXT | grep -vn keyCore | gawk -v cmd="sqlcmd -S%serverEsc% -d%dbname% -U%user% -P%pass% -iSqlObjects\\" "{print cmd $5}" | cmd >> %logFile%
dir SqlObjects\ /b | grep ~4.TXT | sed "s/~/ /g" | gawk -v cmd="sqlcmd -S%serverEsc% -d%dbname% -U%user% -P%pass% -Q\"" -v cmde="\"" -v c1="drop " -v c2=" dbo." "{print cmd c1 $2 c2 $1 cmde}" | sed "s/ScalarFunction/Function/" | sed "s/TableFunction/Function/"
dir SqlObjects\ | grep ~5.TXT | grep -vn keyCore | gawk -v cmd="sqlcmd -S%serverEsc% -d%dbname% -U%user% -P%pass% -iSqlObjects\\" "{print cmd $5}" | cmd >> %logFile%
dir SqlObjects\ /b | grep ~5.TXT | sed "s/~/ /g" | gawk -v cmd="sqlcmd -S%serverEsc% -d%dbname% -U%user% -P%pass% -Q\"" -v cmde="\"" -v c1="drop " -v c2=" dbo." "{print cmd c1 $2 c2 $1 cmde}" | sed "s/ScalarFunction/Function/" | sed "s/TableFunction/Function/"
sqlcmd -S%server% -d%dbname% -U%user% -P%pass% -Q"exec dbo.glCreateTables"
sqlcmd -S%server% -d%dbname% -U%user% -P%pass% -Q"exec dbo.keyUpdateAll" | grep @code=
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
:blankuser
echo Sorry, your missing the user (check your ini)
GOTO:finish
:blankpass
echo Sorry, your missing the password (check your ini)
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
