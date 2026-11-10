$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$startupFolder = [Environment]::GetFolderPath("Startup")
$shortcutPath = Join-Path $startupFolder "Antigravity Pet.lnk"

$wshShell = New-Object -ComObject WScript.Shell
$shortcut = $wshShell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = "wscript.exe"
$shortcut.Arguments = "`"$scriptDir\run_pet_hidden.vbs`""
$shortcut.WorkingDirectory = $scriptDir
$shortcut.IconLocation = "$scriptDir\icon.ico,0"
$shortcut.Description = "Antigravity 2.0 Desktop Pet Interactive Shortcut"
$shortcut.Save()

Write-Host "Antigravity Pet will now launch automatically on Windows startup!" -ForegroundColor Green
Write-Host "Shortcut created in: $shortcutPath"
