@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  call setup.cmd
  if errorlevel 1 exit /b 1
)
".venv\Scripts\python.exe" -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:9235/json/version',timeout=2).close()" >nul 2>nul
if errorlevel 1 (
  ".venv\Scripts\python.exe" -u coretax.py %*
) else (
  ".venv\Scripts\python.exe" -u coretax.py --reuse-browser http://127.0.0.1:9235 %*
)
set RESULT=%ERRORLEVEL%
echo.
if "%RESULT%"=="0" echo Export completed and Excel verified.
if "%RESULT%"=="2" echo Partial export. Open the workbook Audit sheet before relying on totals.
if "%RESULT%"=="1" echo Export blocked. Read the error above.
pause
exit /b %RESULT%
