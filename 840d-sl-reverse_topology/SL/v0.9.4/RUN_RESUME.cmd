@echo off
setlocal
cd /d "%~dp0"
set /p HOST=NCU IP address (must match original): 
set /p CAPTURE=Existing capture folder (e.g. runs\20261025T090000Z): 
if "%HOST%"=="" exit /b 1
if "%CAPTURE%"=="" exit /b 1
if not exist ".venv\Scripts\python.exe" exit /b 1
if not exist "%CAPTURE%\capture.json" (
  echo Legacy capture detected. It must be adopted explicitly.
  .venv\Scripts\python.exe -m topology092 live --host "%HOST%" --out "%CAPTURE%" --resume --adopt-legacy
) else (
  .venv\Scripts\python.exe -m topology092 live --host "%HOST%" --out "%CAPTURE%" --resume
)
set "EXITCODE=%ERRORLEVEL%"
echo.
echo Finished with code %EXITCODE%. All logs stay in %CAPTURE%.
pause
exit /b %EXITCODE%
