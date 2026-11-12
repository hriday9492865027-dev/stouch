# Digital Touchpad - Windows Firewall Configuration Helper (PRD v2.0 Section 10)
# Configures inbound rule for Port 8000 to allow phone connection over local Wi-Fi.

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  Digital Touchpad - Windows Defender Firewall Setup" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

$RuleName = "Digital Touchpad Receiver (Port 8000)"
$Port = 8000

# Check if rule exists
$ExistingRule = Get-NetFirewallRule -DisplayName $RuleName -ErrorAction SilentlyContinue

if ($ExistingRule) {
    Write-Host "[OK] Firewall rule '$RuleName' already exists and is active." -ForegroundColor Green
} else {
    Write-Host "[...] Creating inbound rule for Port $Port on Private and Domain networks..." -ForegroundColor Yellow
    try {
        New-NetFirewallRule -DisplayName $RuleName `
            -Direction Inbound `
            -LocalPort $Port `
            -Protocol TCP `
            -Action Allow `
            -Profile Domain, Private `
            -Description "Allows phone connection to Digital Touchpad companion receiver." -ErrorAction Stop
        Write-Host "[SUCCESS] Inbound rule created successfully for Port $Port!" -ForegroundColor Green
    } catch {
        Write-Host "[!] Could not automatically create rule: $($_.Exception.Message)" -ForegroundColor Red
        Write-Host "To allow manually, open Windows Security -> Firewall & network protection -> Allow an app through firewall." -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "Receiver is ready to accept connections on port $Port." -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

