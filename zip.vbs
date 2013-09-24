'Get command-line arguments.
Set objArgs = WScript.Arguments
InputFile = objArgs(0)
ZipFile = objArgs(1)

'Create empty ZIP file.
CreateObject("Scripting.FileSystemObject").CreateTextFile(ZipFile, True).Write "PK" & Chr(5) & Chr(6) & String(18, vbNullChar)

Set objShell = CreateObject("Shell.Application")

objShell.NameSpace(ZipFile).CopyHere(InputFile)

'Required!
wScript.Echo "hang on a sec.."
wScript.Sleep 5000

zipFileCount = objShell.NameSpace(ZipFile).items.Count

'Keep script waiting until Compressing is done
sLoop = 0
Do Until zipFileCount < objShell.NameSpace(zipFile).Items.Count
  Wscript.Sleep(100)
  sLoop = sLoop + 1
Loop