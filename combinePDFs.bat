@@echo off
set gs="C:\Program Files\Bullzip\PDF Printer\gs\gswin32c.exe"
set tempFile="..\aaatempFile.txt"
set scratch=c:\client\aaa.pdf
set final=c:\client\final.pdf
set pdfFolder="c:\client\taxStatements"
set pdfFolderEsc=%pdfFolder:\=\\%
set options="-q -dNOPAUSE -dBATCH -sDEVICE=pdfwrite"

for /R %pdfFolder% %%i IN (*.*) DO (
    %gs% -q -dNOPAUSE -dBATCH -sDEVICE=pdfwrite -sOutputFile=%final% %scratch% %%i
    echo ren %final% aaa.pdf
)
rem set nextFileName=
















rem echo -q -dNOPAUSE -dBATCH -sDEVICE=pdfwrite -sOutputFile=%scratch% > %tempfile%
rem dir %pdfFolder%\*.pdf /b /on | gawk -v cmd="%pdfFolderEsc%\\" "{print cmd$0}" >> %tempFile%

rem %gs% @%tempFile%
rem del %tempFile%
