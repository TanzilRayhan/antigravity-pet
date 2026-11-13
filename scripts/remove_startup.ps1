$startupFolder = [Environment]::GetFolderPath("Startup")
$shortcutPath = Join-Path $startupFolder "Antigravity Pet.lnk"

if (Test-Path $shortcutPath) {
    Remove-Item -Path $shortcutPath -Force
    Write-Host "Removed Antigravity Pet from Windows Startup: $shortcutPath" -ForegroundColor Yellow
} else {
    Write-Host "Antigravity Pet was not found in Windows Startup folder." -ForegroundColor Gray
}
