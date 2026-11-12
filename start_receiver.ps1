# Digital Touchpad PowerShell Launcher
Set-Location -Path "$PSScriptRoot\server"
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "  Starting Digital Touchpad Companion Receiver (PRD v2.0)" -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan
python app.py

