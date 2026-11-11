@echo off
cd /d "%~dp0"
echo CAUTION: previous PCU drive alarms followed DDE experiments. Cause not proven.
echo Only proceed with machine secured and responsible operator approval.
echo No movement, one read request only. No NCDDE configuration changes.
set CONFIRM=
set /p CONFIRM=Type READ to permit the drive MD test: 
if /I not "%CONFIRM%"=="READ" (
 echo CANCELLED.
 pause
 exit /b 1
)
call "%~dp0RUN_TEST.cmd" 08_MD_DRIVE_PRE binary
