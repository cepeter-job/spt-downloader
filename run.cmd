@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  call setup.cmd
  if errorlevel 1 exit /b 1
)
rem Browser reuse is never inferred from a listener on localhost.
rem Pass --reuse-browser explicitly only with a dedicated Chromium profile.
".venv\Scripts\python.exe" -u coretax.py %*
set RESULT=%ERRORLEVEL%
echo.
if "%RESULT%"=="0" echo Export completed and Excel verified.
if "%RESULT%"=="2" echo Partial export. Open the workbook Audit sheet before relying on totals.
if "%RESULT%"=="1" echo Export blocked. Read the error above.
pause
exit /b %RESULT%
