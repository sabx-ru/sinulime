@echo off
setlocal
cd /d "%~dp0"
set "HOST=%~1"
if "%HOST%"=="" set /p HOST=NCU IP address: 
if "%HOST%"=="" exit /b 1
if not exist ".venv\Scripts\python.exe" (
  echo Run INSTALL.cmd first.
  pause
  exit /b 1
)
.venv\Scripts\python.exe -m topology092 live --host "%HOST%"
set "EXITCODE=%ERRORLEVEL%"
echo.
echo Output is in runs\YYYYMMDDTHHMMSSZ - keep this folder to resume.
echo Finished with code %EXITCODE%.
pause
exit /b %EXITCODE%
