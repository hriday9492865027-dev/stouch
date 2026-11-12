@echo off
title Digital Touchpad - Firewall Setup
netsh advfirewall firewall add rule name="Digital Touchpad Receiver" dir=in action=allow protocol=TCP localport=8000 profile=private,domain
echo ============================================================
echo   Firewall rule for Port 8000 configured!
echo ============================================================
pause

