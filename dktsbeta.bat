if exist uktsbeta.exe del uktsbeta.exe
  
pkzipc -add -sfx -dir ..\uktsbeta c:\client\key\kts\*.*
 
rem ftp -n -s:ktsbeta.ftp 

copy ..\uktsbeta.exe \\192.168.1.14\ftp.kellpro.com\pub\updates
pause 





