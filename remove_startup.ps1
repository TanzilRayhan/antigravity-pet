$startupFolder = [Environment]::GetFolderPath("Startup")
$shortcutPath = Join-Path $startupFolder "Antigravity Pet.lnk"

if (Test-Path $shortcutPath) {
    Remove-Item $shortcutPath -Force
    Write-Host "Removed Antigravity Pet from Windows Startup." -ForegroundColor Yellow
} else {
    Write-Host "Antigravity Pet was not in Startup." -ForegroundColor Gray
}
