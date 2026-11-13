Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
strScriptDir = fso.GetParentFolderName(WScript.ScriptFullName)

If LCase(fso.GetFileName(strScriptDir)) = "scripts" Then
    strRoot = fso.GetParentFolderName(strScriptDir)
Else
    strRoot = strScriptDir
End If

WshShell.CurrentDirectory = strRoot

pyExe = ""
If fso.FileExists(strRoot & "\.venv\Scripts\pythonw.exe") Then
    pyExe = strRoot & "\.venv\Scripts\pythonw.exe"
ElseIf fso.FileExists(strRoot & "\.venv\Scripts\python.exe") Then
    pyExe = strRoot & "\.venv\Scripts\python.exe"
ElseIf fso.FileExists("C:\Users\User\AppData\Local\hermes\hermes-agent\venv\Scripts\pythonw.exe") Then
    pyExe = "C:\Users\User\AppData\Local\hermes\hermes-agent\venv\Scripts\pythonw.exe"
ElseIf fso.FileExists("C:\Users\User\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe") Then
    pyExe = "C:\Users\User\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe"
Else
    pyExe = "pythonw.exe"
End If

mainPy = strRoot & "\main.py"
WshShell.Run """" & pyExe & """ """ & mainPy & """", 0, False
