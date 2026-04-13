@echo off
call "%~dp0..\catalog.bat" import fixtures\sample_releases.csv .catalog-data
exit /b %ERRORLEVEL%
