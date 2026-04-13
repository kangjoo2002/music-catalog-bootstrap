@echo off
call "%~dp0..\catalog.bat" plan fixtures\sample-target.properties .catalog-data
exit /b %ERRORLEVEL%
