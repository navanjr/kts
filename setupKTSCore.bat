@echo off
set /P dbname=What is the database name?
echo %dbname%

sqlcmd -H. -d master -Usa -P America#1 -Q"drop database %dbname%"
sqlcmd -H. -d master -Usa -P America#1 -Q"create database %dbname%"

sqlcmd -H. -d %dbname% -Usa -P America#1 -i C:\client\key\kts\SqlObjects\enableAdvancedSQLOptions~Procedure~1.txt
sqlcmd -H. -d %dbname% -Usa -P America#1 -Q"exec dbo.enableAdvancedSQLOptions"
sqlcmd -H. -d %dbname% -Usa -P America#1 -i C:\client\key\kts\SqlObjects\keyCore~Script~2.txt

dir SqlObjects | grep ~Procedure~1 | gawk "{print $5}"

