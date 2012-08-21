@echo off
set /P dbname=What is the database name?
echo %dbname%

sqlcmd -H. -d master -Usa -P America#1 -Q"drop database %dbname%"
sqlcmd -H. -d master -Usa -P America#1 -Q"create database %dbname%"

sqlcmd -H. -d %dbname% -Usa -P America#1 -i C:\client\key\kts\SqlObjects\enableAdvancedSQLOptions~Procedure~1.txt
sqlcmd -H. -d %dbname% -Usa -P America#1 -Q"exec dbo.enableAdvancedSQLOptions"
sqlcmd -H. -d %dbname% -Usa -P America#1 -i C:\client\key\kts\SqlObjects\keyCore~Script~2.txt

bcp %dbname%.dbo.template in "Needed\bcpTemplate.txt" -Usa -PAmerica#1 -c
