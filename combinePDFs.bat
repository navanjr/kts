@@echo off
setlocal ENABLEDELAYEDEXPANSION
set gs="C:\Program Files\Bullzip\PDF Printer\gs\gswin32c.exe"
set gsBatch="_gsBatch.txt"
set files=_files.txt
set final=_final.tba
set pdfFolder="C:\client\2012_PDFs_TO_BE_COMBINED"
set pdfFolderEsc=%pdfFolder:\=\\%
set options="-q -dNOPAUSE -dBATCH -sDEVICE=pdfwrite"
set /a xCount=0
set /a bCount=1

pushd %pdfFolder%
mkdir processed > nul

:preComp
echo Processing 200 files...
dir *.pdf /b /on | head -n 200  > %files%
for /f %%F in ("%files%") do if %%~zF equ 0 GOTO postComp
echo -q -dNOPAUSE -dBATCH -sDEVICE=pdfwrite -sOutputFile=_preComp%bCount%.tba > %gsBatch%
type %files% >> %gsBatch%
%gs% @%gsBatch%
call:moveFiles
set /a bCount=bCount+1
GOTO:preComp

:postComp
echo Processing preComp files...
dir *.tba /b /on | head -n 200  > %files%
echo -q -dNOPAUSE -dBATCH -sDEVICE=pdfwrite -sOutputFile=final.pdf > %gsBatch%
type %files% >> %gsBatch%
%gs% @%gsBatch%
GOTO:finish
GOTO:EOF


:moveFiles
for /f "tokens=* delims= " %%a in (%files%) do (
    set /a xCount=xCount+1
    echo !xCount! %%a
    move /Y %%a processed\%%a > nul
)
GOTO:EOF

:finish
del %files%
del %gsBatch%
echo finished
popd
endlocal
GOTO:EOF

rem| gawk -v cmd="%pdfFolderEsc%\\" "{print cmd$0}"

rem for /R %pdfFolder% %%i IN (*.*) DO (
rem    echo %%i
rem    %gs% -q -dNOPAUSE -dBATCH -sDEVICE=pdfwrite -sOutputFile=%final% %scratch% %%i
rem    del %scratch%
rem    ren %final% aaa.pdf
rem )
rem set nextFileName=
















rem echo -q -dNOPAUSE -dBATCH -sDEVICE=pdfwrite -sOutputFile=%scratch% > %tempfile%

rem %gs% @%tempFile%
rem del %tempFile%
