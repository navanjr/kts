@ECHO OFF
FOR /F "tokens=3 delims=: " %%H IN ('SC QUERY "aaa_kellpro_notice" ^| FINDSTR "        STATE"') DO (
  IF /I "%%H" NEQ "RUNNING" (
   NET START "aaa_kellpro_notice"
  )
)