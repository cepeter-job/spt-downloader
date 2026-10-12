@echo off
setlocal
cd /d "%~dp0"
where uv >nul 2>nul
if errorlevel 1 (
  echo uv 0.12.22 diperlukan. Panduan instalasi: https://docs.astral.sh/uv/getting-started/installation/
  pause
  exit /b 1
)
powershell -NoProfile -NonInteractive -Command "$version = (& uv --version) -replace '^uv ([0-9]+\.[0-9]+\.[0-9]+).*','$1'; if ($LASTEXITCODE -ne 0 -or $version -ne '0.12.22') { exit 1 }"
if errorlevel 1 (
  echo Gunakan uv 0.12.22 sesuai pin aplikasi dan katalog Python yang sudah diverifikasi.
  pause
  exit /b 1
)
rem Python 3.11 Windows resmi berhenti di 3.11.9; distribusi managed menyediakan patch 3.11.17.
uv python install 3.11.17+gil --no-bin --no-registry
if errorlevel 1 exit /b 1
rem Hanya environment proyek yang disiapkan ulang; Python sistem tidak diubah.
uv venv --managed-python --python 3.11.17+gil --clear .venv
if errorlevel 1 exit /b 1
uv pip sync --python ".venv\Scripts\python.exe" --require-hashes --only-binary :all: locks/runtime.txt
if errorlevel 1 exit /b 1
echo Persiapan selesai. Microsoft Edge atau Google Chrome perlu tersedia.
echo Jalankan run.cmd untuk memasukkan NPWP dan tahun pajak.
pause
