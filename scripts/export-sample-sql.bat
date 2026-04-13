@echo off
call "%~dp0..\catalog.bat" export-sql fixtures\sample-target.properties out\sample-target.sql .catalog-data
exit /b %ERRORLEVEL%
