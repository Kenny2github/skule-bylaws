@echo off

python scripts\mds_to_html.py
if ERRORLEVEL 1 exit /b %ERRORLEVEL%
xcopy scripts\static build /S /I /Y
if ERRORLEVEL 1 exit /b %ERRORLEVEL%
xcopy scripts\images build\images /S /I /Y
if ERRORLEVEL 1 exit /b %ERRORLEVEL%
