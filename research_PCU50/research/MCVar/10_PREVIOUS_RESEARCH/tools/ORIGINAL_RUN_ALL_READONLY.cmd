@echo off
setlocal
set ROOT=%~dp0
if "%1"=="" goto offline
if /I "%1"=="offline" goto offline
if /I "%1"=="capabilities" goto capabilities
if /I "%1"=="smoke" goto blocked
if /I "%1"=="benchmark" goto blocked
if /I "%1"=="subscription" goto blocked
echo Usage: RUN_ALL_READONLY.cmd [offline^|capabilities^|smoke^|benchmark^|subscription]
exit /b 2
:offline
if not exist "%ROOT%logs" mkdir "%ROOT%logs"
>"%ROOT%logs\offline_validation.jsonl" echo {"test_id":"phase13-offline","status":"NOT_RUN","reason":"No offline input configured"}
echo Offline-only run recorded. No PCU or COM access performed.
exit /b 0
:capabilities
if not exist "%ROOT%bin\mcvar_typeinfo_probe.exe" (
  echo Build mcvar_typeinfo_probe.exe first.
  exit /b 3
)
"%ROOT%bin\mcvar_typeinfo_probe.exe" MCVar.Var2 > "%ROOT%logs\typeinfo.jsonl"
exit /b %ERRORLEVEL%
:blocked
echo This mode requires a separately authorized matching Windows/PCU test and explicit bounded configuration.
exit /b 4
