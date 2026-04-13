@echo off
setlocal
python scripts\prepublish-check.py
exit /b %ERRORLEVEL%
