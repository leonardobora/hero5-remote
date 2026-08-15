@echo off
setlocal
set /p SSID="GoPro Wi-Fi name (SSID): "
set /p PASS="GoPro Wi-Fi password: "
powershell -ExecutionPolicy Bypass -Command "Start-Process powershell -Verb runAs -ArgumentList '-ExecutionPolicy Bypass -File \"%~dp0connect-and-route.ps1\" -Ssid \"%SSID%\" -Password \"%PASS%\"'"
endlocal
