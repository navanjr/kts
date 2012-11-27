@@echo off
set gs="C:\Program Files\Bullzip\PDF Printer\gs\gswin32c.exe"
set tempFile="..\aaatempFile.txt"
set scratch="c:\client\aaa.pdf"
set final="..\final.pdf"
set pdfFolder="c:\client\taxStatements"
set pdfFolderEsc=%pdfFolder:\=\\%

echo -q -dNOPAUSE -dBATCH -sDEVICE=pdfwrite -sOutputFile=%scratch% > %tempfile%
dir %pdfFolder%\*.pdf /b /on | gawk -v cmd="%pdfFolderEsc%\\" "{print cmd$0}" >> %tempFile%
REM dir %pdfFolder%\*.pdf /b /on >> %tempFile%

%gs% @%tempFile%
del %tempFile%

REM dir /B /ON %pdfFolder% | grep .pdf | head -n 10 > tempFile.txt
REM set /p myvar= < %tempFile%

REM echo %myvar%

REM SETLOCAL ENABLEDELAYEDEXPANSION
REM set FILES=
REM for /f %%a IN ('dir /b /on %pdfFolder% ^| head -n 10 ^| gawk "{print \"%pdfFolder%\" $0}"') do set FILES=!FILES! %%a
REM echo %FILES%
REM %gs% -q -dNOPAUSE -dBATCH -sDEVICE=pdfwrite -sOutputFile=%scratch% %FILES%

