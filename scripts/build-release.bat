@echo off
setlocal

set "ROOT=%~dp0.."
pushd "%ROOT%" >nul

where py >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    py -3 "%ROOT%\scripts\build-release.py"
) else (
    python "%ROOT%\scripts\build-release.py"
)
set "EXIT_CODE=%ERRORLEVEL%"
popd >nul
exit /b %EXIT_CODE%
