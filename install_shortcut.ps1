$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$desktop = [Environment]::GetFolderPath("Desktop")
$shortcutPath = Join-Path $desktop "Antigravity Pet.lnk"

$wshShell = New-Object -ComObject WScript.Shell
$shortcut = $wshShell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = "wscript.exe"
$shortcut.Arguments = "`"$scriptDir\run_pet_hidden.vbs`""
$shortcut.WorkingDirectory = $scriptDir
$shortcut.IconLocation = "$scriptDir\icon.ico,0"
$shortcut.Description = "Antigravity 2.0 Desktop Pet Interactive Shortcut"
$shortcut.Save()

Write-Host "Created Desktop Shortcut at: $shortcutPath" -ForegroundColor Green
