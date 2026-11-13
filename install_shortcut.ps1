$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition

$exeTarget = Join-Path $scriptDir "release\AntigravityPet-v2.2.0-Portable\AntigravityPet.exe"
if (-not (Test-Path $exeTarget)) {
    $exeTarget = (Get-ChildItem -Path (Join-Path $scriptDir "release") -Filter "AntigravityPet.exe" -Recurse -ErrorAction SilentlyContinue | Select-Object -Last 1).FullName
}
if (Test-Path $exeTarget) {
    $targetPath = $exeTarget
    $targetArgs = ""
} else {
    $targetPath = "wscript.exe"
    $targetArgs = "`"$scriptDir\run_pet_hidden.vbs`""
}

$wshShell = New-Object -ComObject WScript.Shell

# 1. Desktop
$desktop = [Environment]::GetFolderPath("Desktop")
$dtShortcutPath = Join-Path $desktop "Antigravity Pet.lnk"
$sc1 = $wshShell.CreateShortcut($dtShortcutPath)
$sc1.TargetPath = $targetPath
$sc1.Arguments = $targetArgs
$sc1.WorkingDirectory = $scriptDir
$sc1.IconLocation = "$scriptDir\icon.ico,0"
$sc1.Description = "Antigravity 2.0 Desktop Pet Interactive Shortcut"
$sc1.Hotkey = "Ctrl+Alt+P"
$sc1.Save()

# 2. Start Menu Programs
$programs = [Environment]::GetFolderPath("Programs")
$smShortcutPath = Join-Path $programs "Antigravity Pet.lnk"
$sc2 = $wshShell.CreateShortcut($smShortcutPath)
$sc2.TargetPath = $targetPath
$sc2.Arguments = $targetArgs
$sc2.WorkingDirectory = $scriptDir
$sc2.IconLocation = "$scriptDir\icon.ico,0"
$sc2.Description = "Antigravity 2.0 Desktop Pet Interactive Shortcut"
$sc2.Hotkey = "Ctrl+Alt+P"
$sc2.Save()

Write-Host "Created Desktop & Start Menu Shortcuts with Hotkey Ctrl+Alt+P (Zero Terminal)" -ForegroundColor Green
