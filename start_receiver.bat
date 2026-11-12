@echo off
title Digital Touchpad - Windows Companion Receiver
cd /d "%~dp0server"
echo ========================================================
echo   Starting Digital Touchpad Companion Receiver...
echo ========================================================
python app.py
pause

