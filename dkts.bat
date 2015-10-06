if exist ..\ukts.exe del ..\ukts.exe
  
pkzipc -add -sfx -dir ..\ukts c:\client\key\kts\reports\*.* c:\client\key\kts\templates\*.* c:\client\key\kts\sqlobjects\*.* c:\client\key\kts\kts.bat c:\client\key\kts\*.py c:\client\key\kts\*.ftp
 
rem ftp -n -s:kts.ftp 
copy ..\ukts.exe \\192.168.1.14\ftp.kellpro.com\pub\updates
pause 





