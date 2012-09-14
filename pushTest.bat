@echo off
@setlocal enableextensions enabledelayedexpansion
set TERM=msys

set val=
call :getIni ..\keyGit.ini git testServer
set server=%val%
set val=
call :getIni ..\keyGit.ini git testUser
set user=%val%
set val=
call :getIni ..\keyGit.ini git testPass
set pass=%val%

set connString=-S%server% -U%user% -P%pass%

:displayMenu
echo.
rem call git show --oneline --decorate
echo  =================================
echo       Push to Testing Server
echo   (%connString%)
echo  =================================
echo.
echo   [C]reate or [P]ush
echo.
echo     1. Roger Mills
echo.
echo.

set /P menuOption=please choose wisely:
IF /I "%menuOption%"=="Q" GOTO finish
IF /I "%menuOption%"=="P1" call :pushObjectsAll rogermills
IF /I "%menuOption%"=="C1" call :create rogermills
GOTO:displayMenu

:pushObjectsAll
set dbname=%1
call :pushObjects ~1.TXT %dbname%
call :pushObjects ~2.TXT %dbname%
call :pushObjects ~3.TXT %dbname%
call :pushObjects ~4.TXT %dbname%
call :pushObjects ~5.TXT %dbname%
sqlcmd %connString% -d%dbname% -Q"exec dbo.glCreateTables"
GOTO:EOF

:pushObjects
 set orderString=%1
 set dbname=%2
 dir SqlObjects\ /b | grep -v keyCore | grep %orderString% | sed "s/~/ /g" | gawk -v cmd="sqlcmd %connString% -d%dbname% -Q\"" -v cmde="\"" -v c1="drop " -v c2=" dbo." "{print cmd c1 $2 c2 $1 cmde}" | sed "s/ScalarFunction/Function/" | sed "s/TableFunction/Function/" | cmd
 dir sqlObjects\ /b | grep -v keyCore | grep %orderString% | gawk -v cmd="sqlcmd %connString% -d%dbname% -iSqlObjects\\" "{print cmd $1}" | cmd
GOTO:EOF

:create
set dbname=%1
rem CREATE THE NEW DATABASE
 sqlcmd %connString% -dmaster -Q"alter database %dbname% set single_user with rollback immediate"
 sqlcmd %connString% -dmaster -Q"drop database %dbname%"
 sqlcmd %connString% -dmaster -Q"create database %dbname%"
rem CREATE THE APPLICATION USER
 sqlcmd %connString% -d%dbname% -Q"drop login ktsUser"
 sqlcmd %connString% -d%dbname% -Q"create login ktsUser WITH PASSWORD=N'VIPER', DEFAULT_DATABASE=[master], CHECK_EXPIRATION=OFF, CHECK_POLICY=OFF"
 sqlcmd %connString% -d%dbname% -Q"exec master..sp_addsrvrolemember @loginame = N'ktsUser', @rolename = N'sysadmin'"
rem TWEAK SQL ENVIRONMENT
 sqlcmd %connString% -d%dbname% -i C:\client\key\kts\SqlObjects\enableAdvancedSQLOptions~Procedure~1.txt
 sqlcmd %connString% -d%dbname% -Q"exec dbo.enableAdvancedSQLOptions"
 sqlcmd %connString% -d%dbname% -i C:\client\key\kts\SqlObjects\keyCore~Script~2.txt
 sqlcmd %connString% -d%dbname% -Q"insert object (typ,link1,b13,b14) select 0,-1,'@gitPath=c:\client\kts;','@gitCommitter=FALSE;'"
GOTO:EOF




:finish
popd
endlocal
GOTO:EOF

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
