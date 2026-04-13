@echo off
setlocal

set "ROOT=%~dp0"
set "PYTHONPATH=%ROOT%src;%PYTHONPATH%"

where py >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    py -3 -m music_catalog_bootstrap %*
    exit /b %ERRORLEVEL%
)

python -m music_catalog_bootstrap %*
exit /b %ERRORLEVEL%
