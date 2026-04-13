@echo off
setlocal
powershell -ExecutionPolicy Bypass -File "%~dp0smoke-apply.ps1" %*
exit /b %ERRORLEVEL%
