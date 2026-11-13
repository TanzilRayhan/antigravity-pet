$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
if ((Split-Path -Leaf $scriptDir).ToLower() -eq "scripts") {
    $projectRoot = Split-Path -Parent $scriptDir
} else {
    $projectRoot = $scriptDir
}

$pywExe = "$projectRoot\.venv\Scripts\pythonw.exe"
if (-not (Test-Path $pywExe)) {
    $pywExe = "$env:LOCALAPPDATA\hermes\hermes-agent\venv\Scripts\pythonw.exe"
}
if (-not (Test-Path $pywExe)) {
    $pywExe = (Get-Command pythonw.exe -ErrorAction SilentlyContinue).Source
}
if (-not $pywExe) {
    $pywExe = "wscript.exe"
    $pywArgs = "`"$projectRoot\run_pet_hidden.vbs`""
} else {
    $pywArgs = "`"$projectRoot\main.py`""
}

$iconTarget = Join-Path $projectRoot "assets\icon.ico"
if (-not (Test-Path $iconTarget)) {
    $iconTarget = Join-Path $projectRoot "icon.ico"
}

$startupFolder = [Environment]::GetFolderPath("Startup")
$shortcutPath = Join-Path $startupFolder "Antigravity Pet.lnk"

$wshShell = New-Object -ComObject WScript.Shell
$shortcut = $wshShell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $pywExe
$shortcut.Arguments = $pywArgs
$shortcut.WorkingDirectory = $projectRoot
$shortcut.IconLocation = "$iconTarget,0"
$shortcut.Description = "Antigravity 2.0 Desktop Pet Interactive Shortcut"
$shortcut.Hotkey = "Ctrl+Alt+P"
$shortcut.Save()

Write-Host "Antigravity Pet configured for Windows startup: $shortcutPath" -ForegroundColor Green
