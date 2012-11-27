@@echo off
set gs="C:\Program Files\Bullzip\PDF Printer\gs\gswin32c.exe"
set tempFile="..\aaatempFile.txt"
set scratch="c:\client\aaa.pdf"
set final="..\final.pdf"
set pdfFolder="c:\client\taxStatements"
set pdfFolderEsc=%pdfFolder:\=\\%

echo -q -dNOPAUSE -dBATCH -sDEVICE=pdfwrite -sOutputFile=%scratch% > %tempfile%
dir %pdfFolder%\*.pdf /b /on | gawk -v cmd="%pdfFolderEsc%\\" "{print cmd$0}" >> %tempFile%

%gs% @%tempFile%
del %tempFile%
