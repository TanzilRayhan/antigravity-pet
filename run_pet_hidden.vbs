Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
strPath = fso.GetParentFolderName(WScript.ScriptFullName)
WshShell.CurrentDirectory = strPath

pyExe = ""
If fso.FileExists(strPath & "\.venv\Scripts\pythonw.exe") Then
    pyExe = strPath & "\.venv\Scripts\pythonw.exe"
ElseIf fso.FileExists(strPath & "\.venv\Scripts\python.exe") Then
    pyExe = strPath & "\.venv\Scripts\python.exe"
ElseIf fso.FileExists("C:\Users\User\AppData\Local\hermes\hermes-agent\venv\Scripts\pythonw.exe") Then
    pyExe = "C:\Users\User\AppData\Local\hermes\hermes-agent\venv\Scripts\pythonw.exe"
ElseIf fso.FileExists("C:\Users\User\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe") Then
    pyExe = "C:\Users\User\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe"
Else
    pyExe = "pythonw.exe"
End If

mainPy = strPath & "\main.py"
WshShell.Run """" & pyExe & """ """ & mainPy & """", 0, False
