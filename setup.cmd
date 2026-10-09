@echo off
setlocal
cd /d "%~dp0"
where uv >nul 2>nul
if errorlevel 1 (
  echo uv is required. Install uv from https://docs.astral.sh/uv/getting-started/installation/
  pause
  exit /b 1
)
if not exist ".venv\Scripts\python.exe" (
  uv venv --python 3.11 .venv
  if errorlevel 1 exit /b 1
)
uv pip install --python ".venv\Scripts\python.exe" -r requirements.txt
if errorlevel 1 exit /b 1
echo Setup complete. Microsoft Edge or Google Chrome must be installed.
echo Run run.cmd to enter NPWP and tax year.
pause
