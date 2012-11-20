@echo off
set TERM=msys
pushd c:\client\key\kts
echo [gitInfo] > ..\gitInfo.ini
for /F "tokens=3 delims=/" %%i in (.git/HEAD) do echo BRANCHNAME=%%i >> ..\gitInfo.ini
call git tag > ..\gitTags.txt
call sed -n -e ":a" -e "$ s/\n/|/gp;N;b a" ..\gitTags.txt > ..\gitTagsLine.txt
call git describe --tags > ..\gitStatus.txt
call git status >> ..\gitStatus.txt
call git log --oneline --decorate -n20 --date=short > ../gitLog.txt
popd
