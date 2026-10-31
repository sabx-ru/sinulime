@echo off
setlocal
cd /d "%~dp0"
if not exist stage15_diag.exe (
  echo Missing stage15_diag.exe. Build on Debian with BUILD_DEBIAN.sh.
  exit /b 2
)
stage15_diag.exe > results_async.jsonl
if errorlevel 1 exit /b %errorlevel%
