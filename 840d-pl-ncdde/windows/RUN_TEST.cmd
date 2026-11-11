@echo off
setlocal
cd /d "%~dp0"
if "%~1"=="" goto usage
if not exist logs mkdir logs
if not exist "bin\ncdde_md_probe.exe" (
 echo ERROR: build program on Debian and copy windows directory.
 goto failed
)
set TESTNAME=%~1
set FORMAT=%~2
if "%FORMAT%"=="" set FORMAT=binary
if not exist "sets\%TESTNAME%.txt" (
 echo ERROR: set file not found: sets\%TESTNAME%.txt
 goto failed
)
echo ================================
echo NCDDE read-only single request
echo Set: %TESTNAME%
echo Format: %FORMAT%
echo ================================
bin\ncdde_md_probe.exe --items=sets\%TESTNAME%.txt --label=%TESTNAME% --topic=machineswitch --format=%FORMAT% --timeout=3000
if errorlevel 1 (
 echo FAILED: see logs for details.
 goto failed
)
echo FINISHED: see logs directory.
pause
exit /b 0
:usage
echo Usage: RUN_TEST.cmd SETNAME [binary^|text]
:failed
pause
exit /b 1
