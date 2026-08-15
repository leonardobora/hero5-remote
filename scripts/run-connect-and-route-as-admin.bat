@echo off
setlocal
set /p SSID="GoPro Wi-Fi name (SSID): "
set /p PASS="GoPro Wi-Fi password: "
powershell -ExecutionPolicy Bypass -Command "Start-Process powershell -Verb runAs -Wait -ArgumentList '-ExecutionPolicy Bypass -File \"%~dp0connect-and-route.ps1\" -Ssid \"%SSID%\" -Password \"%PASS%\"'"
echo.
echo Script finished. Press any key to close.
pause > nul
endlocal
