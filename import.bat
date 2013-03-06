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

GOTO:display

:display
echo ==============================
echo     Options for %dbname%
echo ==============================
echo   [T]est Connection
echo   [I]mport from repo
echo   [G]it Committer
echo   [S]erver's Path to the Repo
echo   ---------
echo   L[o]gging
echo   ---------
echo   [C] Git Commit
echo   [P] Git Pull
echo   [H] Git Push
echo   [U] Git Status
echo   [L] Git Log
echo    e[x]it
echo ------------------------------
SET /P runmode=Please Choose:
IF /I "%runmode%"=="T" call:TestConnection
IF /I "%runmode%"=="I" call:ImportNew
IF /I "%runmode%"=="G" call:SetGitCommitterQ
IF /I "%runmode%"=="S" call:SetServerPath
IF /I "%runmode%"=="C" call:gitCommit
IF /I "%runmode%"=="P" call:gitPull
IF /I "%runmode%"=="U" call:gitStatus
IF /I "%runmode%"=="H" call:gitPush
IF /I "%runmode%"=="L" call:gitLog
IF /I "%runmode%"=="N" call:ImportRepo
IF /I "%runmode%"=="O" call:ConfigureLogging
IF /I "%runmode%"=="DRE" call:dropRecreateExecute
IF /I "%runmode%"=="X" GOTO finish
GOTO:display

:dropRecreateExecute
SET /P sqlObjectName=Please enter SQL Object Name:
SET /P sqlObjectOrder=Please enter the SQL Objects(%sqlObjectName%) Order Number:
echo dropping  dbo.%sqlObjectName%
sqlcmd -S%server% -d%dbname% -U%user% -P%pass% -Q"drop procedure dbo.%sqlObjectName%"
echo creating %sqlObjectName%...
sqlcmd -S%server% -d%dbname% -U%user% -P%pass% -iSqlObjects\%sqlObjectName%~Procedure~%sqlObjectOrder%.TXT
echo calling %sqlObjectName%...
sqlcmd -S%server% -d%dbname% -U%user% -P%pass% -Q"exec dbo.%sqlObjectName%"
GOTO:EOF

:ImportNew
set targetFile=keySQLObjectDispatcher
echo dropping %targetFile%...
sqlcmd -S%server% -d%dbname% -U%user% -P%pass% -Q"drop procedure dbo.%targetFile%"
echo creating %targetFile%...
sqlcmd -S%server% -d%dbname% -U%user% -P%pass% -iSqlObjects\%targetFile%~Procedure~2.TXT

echo dropping keyUpdateAll...
sqlcmd -S%server% -d%dbname% -U%user% -P%pass% -Q"drop procedure dbo.keyUpdateAll"
echo creating keyUpdateAll...
sqlcmd -S%server% -d%dbname% -U%user% -P%pass% -iSqlObjects\keyUpdateAll~Procedure~9999.TXT
echo calling keyUpdateAll...
sqlcmd -S%server% -d%dbname% -U%user% -P%pass% -Q"exec dbo.keyUpdateAll 'NewMethod'"

sqlcmd -S%server% -d%dbname% -U%user% -P%pass% -Q"exec dbo.createIndexes" >> %logFile%
sqlcmd -S%server% -d%dbname% -U%user% -P%pass% -Q"exec dbo.createGroups" >> %logFile%
GOTO:EOF

:gitPush
call git push origin dev --tags
GOTO:EOF

:gitCommit
SET /P gitmsg=Commit message:
call git commit -a -m "key_commit: %gitmsg% "
GOTO:EOF

:gitLog
call git log
GOTO:EOF

:gitStatus
call git status
GOTO:EOF

:gitPull
call git pull origin dev
GOTO:EOF

:SetGitCommitterQ
SET /P qanswer=set gitCommitter? ( [E]nable / [D]isable )
IF /I "%qanswer%"=="E" call :SetGitCommitter TRUE
IF /I "%qanswer%"=="D" call :SetGitCommitter FALSE
GOTO:EOF

:SetServerPath
SET /P newPath=Enter the Path to the Repo from the Server:
sqlcmd -S%server% -d%dbname% -U%user% -P%pass% -Q"update object set b13='@gitPath=%newPath%;' where typ=0 and link1=-1"
echo @gitPath=%newPath%
GOTO:EOF

:ConfigureLogging
sqlcmd -S%server% -d%dbname% -U%user% -P%pass% -Q"exec dbo.logit @control=status"
SET /P qanswer=set logging? ( [E]nable / [D]isable )
IF /I "%qanswer%"=="E" call :SetLoggingE 
IF /I "%qanswer%"=="D" call :SetLoggingD
GOTO:EOF

:SetLoggingE
sqlcmd -S%server% -d%dbname% -U%user% -P%pass% -Q"exec dbo.logit @control='start|1|'"
GOTO:EOF

:SetLoggingD
sqlcmd -S%server% -d%dbname% -U%user% -P%pass% -Q"exec dbo.logit @control=stop"
GOTO:EOF

:SetGitCommitter
set gcValue=%1
sqlcmd -S%server% -d%dbname% -U%user% -P%pass% -Q"update object set b14='@gitCommitter=%gcValue%;' where typ=0 and link1=-1"
echo set @gitCommitter=%gcValue%
GOTO:EOF

:TestConnection
sqlcmd -S%server% -d%dbname% -U%user% -P%pass% -Q"select b13 as gitPath, b14 as gitCommitter from Object where Link1 = -1 and TYP = 0"
GOTO:EOF

:ImportRepo
dir SqlObjects\ /b | grep ~1.TXT | sed "s/~/ /g" | gawk -v cmd="sqlcmd -S%serverEsc% -d%dbname% -U%user% -P%pass% -Q\"" -v cmde="\"" -v c1="drop " -v c2=" dbo." "{print cmd c1 $2 c2 $1 cmde}" | sed "s/ScalarFunction/Function/" | sed "s/TableFunction/Function/" | cmd >> %logFile%
dir SqlObjects\ | grep ~1.TXT | grep -vn keyCore | gawk -v cmd="sqlcmd -S%serverEsc% -d%dbname% -U%user% -P%pass% -iSqlObjects\\" "{print cmd $5}" | cmd >> %logFile%
dir SqlObjects\ /b | grep ~2.TXT | sed "s/~/ /g" | gawk -v cmd="sqlcmd -S%serverEsc% -d%dbname% -U%user% -P%pass% -Q\"" -v cmde="\"" -v c1="drop " -v c2=" dbo." "{print cmd c1 $2 c2 $1 cmde}" | sed "s/ScalarFunction/Function/" | sed "s/TableFunction/Function/" | cmd >> %logFile%
dir SqlObjects\ | grep ~2.TXT | grep -vn keyCore | gawk -v cmd="sqlcmd -S%serverEsc% -d%dbname% -U%user% -P%pass% -iSqlObjects\\" "{print cmd $5}" | cmd >> %logFile%
dir SqlObjects\ /b | grep ~3.TXT | sed "s/~/ /g" | gawk -v cmd="sqlcmd -S%serverEsc% -d%dbname% -U%user% -P%pass% -Q\"" -v cmde="\"" -v c1="drop " -v c2=" dbo." "{print cmd c1 $2 c2 $1 cmde}" | sed "s/ScalarFunction/Function/" | sed "s/TableFunction/Function/" | cmd >> %logFile%
dir SqlObjects\ | grep ~3.TXT | grep -vn keyCore | gawk -v cmd="sqlcmd -S%serverEsc% -d%dbname% -U%user% -P%pass% -iSqlObjects\\" "{print cmd $5}" | cmd >> %logFile%
dir SqlObjects\ /b | grep ~4.TXT | sed "s/~/ /g" | gawk -v cmd="sqlcmd -S%serverEsc% -d%dbname% -U%user% -P%pass% -Q\"" -v cmde="\"" -v c1="drop " -v c2=" dbo." "{print cmd c1 $2 c2 $1 cmde}" | sed "s/ScalarFunction/Function/" | sed "s/TableFunction/Function/" | cmd >> %logFile%
dir SqlObjects\ | grep ~4.TXT | grep -vn keyCore | gawk -v cmd="sqlcmd -S%serverEsc% -d%dbname% -U%user% -P%pass% -iSqlObjects\\" "{print cmd $5}" | cmd >> %logFile%
dir SqlObjects\ /b | grep ~5.TXT | sed "s/~/ /g" | gawk -v cmd="sqlcmd -S%serverEsc% -d%dbname% -U%user% -P%pass% -Q\"" -v cmde="\"" -v c1="drop " -v c2=" dbo." "{print cmd c1 $2 c2 $1 cmde}" | sed "s/ScalarFunction/Function/" | sed "s/TableFunction/Function/" | cmd >> %logFile%
dir SqlObjects\ | grep ~5.TXT | grep -vn keyCore | gawk -v cmd="sqlcmd -S%serverEsc% -d%dbname% -U%user% -P%pass% -iSqlObjects\\" "{print cmd $5}" | cmd >> %logFile%
sqlcmd -S%server% -d%dbname% -U%user% -P%pass% -Q"exec dbo.glCreateTables" >> %logFile%
sqlcmd -S%server% -d%dbname% -U%user% -P%pass% -Q"exec dbo.keyUpdateAll" | grep '@code='
sqlcmd -S%server% -d%dbname% -U%user% -P%pass% -Q"exec dbo.keyCSV import" >> %logFile%
sqlcmd -S%server% -d%dbname% -U%user% -P%pass% -Q"exec dbo.createIndexes" >> %logFile%
sqlcmd -S%server% -d%dbname% -U%user% -P%pass% -Q"exec dbo.createGroups" >> %logFile%
echo "Imported" %date% %time%
if DEFINED dropdll goto dodropdll
call:sendLog
GOTO:EOF

:sendLog
git log -n40 --oneline --decorate | sed s/\n/\r\n/ | sed "s|'||g"  | sed "1iupdate object set e1=\'" | sed "$a\' where typ=0 and link1=-1" > ..\importLog.sql
sqlcmd -S%server% -d%dbname% -U%user% -P%pass% -i ..\importLog.sql
GOTO:EOF

:finish
echo finished
popd
endlocal
GOTO:EOF

:dodropdll
del %dropdll%
echo I dropped it like it was hot
GOTO:EOF

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
