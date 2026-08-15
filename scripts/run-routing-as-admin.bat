@echo off
:: Prompt for Administrator elevation and run the Windows routing configuration.
powershell -ExecutionPolicy Bypass -Command "Start-Process powershell -Verb runAs -ArgumentList '-ExecutionPolicy Bypass -File \"%~dp0configure-windows-routing.ps1\"'"
