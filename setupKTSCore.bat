@echo off
pushd c:\client\key\kts
SETLOCAL ENABLEDELAYEDEXPANSION

set /P server=Where is the server?
set /P dbname=What do you want to name this new database?
set /P userpassentered=What do you want the key RID Password to use? (dont worry about caseing, i will convert to upper for you.)
set /P kppass=What is the Kellpro Support SA Super Secret Password? (this one is case sensitive.)

call :UCase userpassentered userpass

rem CREATE THE NEW DATABASE
 sqlcmd -S%server% -dmaster -Usa -P%kppass% -Q"alter database %dbname% set single_user with rollback immediate"
 sqlcmd -S%server% -dmaster -Usa -P%kppass% -Q"drop database %dbname%"
 sqlcmd -S%server% -dmaster -Usa -P%kppass% -Q"create database %dbname%"

rem CREATE THE APPLICATION USER
 sqlcmd -S%server% -d%dbname% -Usa -P%kppass% -Q"drop login %dbname%User"
 sqlcmd -S%server% -d%dbname% -Usa -P%kppass% -Q"create login %dbname%User WITH PASSWORD=N'%userpass%', DEFAULT_DATABASE=[master], CHECK_EXPIRATION=OFF, CHECK_POLICY=OFF"
 sqlcmd -S%server% -d%dbname% -Usa -P%kppass% -Q"exec master..sp_addsrvrolemember @loginame = N'%dbname%User', @rolename = N'sysadmin'"

rem TWEAK SQL ENVIRONMENT
 sqlcmd -S%server% -d%dbname% -Usa -P%kppass% -i C:\client\key\kts\SqlObjects\enableAdvancedSQLOptions~Procedure~1.txt
 sqlcmd -S%server% -d%dbname% -Usa -P%kppass% -Q"exec dbo.enableAdvancedSQLOptions"

rem SETUP CORE KEY AND KTS TABLES AND SUCH
 sqlcmd -S%server% -d%dbname% -U%dbname%User -P%userpass% -i C:\client\key\kts\SqlObjects\keyCore~Script~2.txt
 sqlcmd -S%server% -d%dbname% -U%dbname%User -P%userpass% -i C:\client\key\kts\SqlObjects\keySQLObjectDispatcher~Procedure~2.txt
 sqlcmd -S%server% -d%dbname% -U%dbname%User -P%userpass% -i C:\client\key\kts\SqlObjects\ridread~ScalarFunction~2.txt
 sqlcmd -S%server% -d%dbname% -U%dbname%User -P%userpass% -i C:\client\key\kts\SqlObjects\ridwrite~ScalarFunction~2.txt
 sqlcmd -S%server% -d%dbname% -U%dbname%User -P%userpass% -i C:\client\key\kts\SqlObjects\getSiteBlob~ScalarFunction~2.txt
 sqlcmd -S%server% -d%dbname% -U%dbname%User -P%userpass% -Q"insert object (typ,link1) select 0,-1"

rem IMPORT TEMPLATES AND USERS
 bcp %dbname%.dbo.template in "Needed\bcpTemplate.txt" -U%dbname%User -P%userpass% -S%server% -n -C1252
 bcp %dbname%.dbo.Users in "Needed\bcpUsers.txt" -U%dbname%User -P%userpass% -S%server% -n -C1252

rem GENERATE RID FILE
 echo sending to ridwrite: database=%dbname%;driver=SQL SERVER;SERVER=%server%;uid=%dbname%User;pwd=%userpass%;
 sqlcmd -S%server% -d%dbname% -U%dbname%User -P%userpass% -o..\%dbname%.rid -Q"select 'ridstring' + dbo.ridwrite('database=%dbname%;driver=SQL SERVER;SERVER=%server%;uid=%dbname%User;pwd=%userpass%;')"
 sed -i /ridstring/^^!d ..\%dbname%.rid
 sed -i s/ridstring// ..\%dbname%.rid
 del sed*

ENDLOCAL
popd
GOTO:EOF


:LCase
:UCase
SET _UCase=A B C D E F G H I J K L M N O P Q R S T U V W X Y Z
SET _LCase=a b c d e f g h i j k l m n o p q r s t u v w x y z
SET _Lib_UCase_Tmp=!%1!
IF /I "%0"==":UCase" SET _Abet=%_UCase%
IF /I "%0"==":LCase" SET _Abet=%_LCase%
FOR %%Z IN (%_Abet%) DO SET _Lib_UCase_Tmp=!_Lib_UCase_Tmp:%%Z=%%Z!
SET %2=%_Lib_UCase_Tmp%
GOTO:EOF