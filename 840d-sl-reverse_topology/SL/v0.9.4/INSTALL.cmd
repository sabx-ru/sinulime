@echo off
setlocal EnableExtensions
cd /d "%~dp0"

rem Accept an existing x64 Python 3.12 or 3.13, even without py.exe.
set "PYTHON_CMD="
call :probe_python python
if defined PYTHON_CMD goto :setup
call :probe_python py -3.13
if defined PYTHON_CMD goto :setup
call :probe_python py -3.12
if defined PYTHON_CMD goto :setup
call :probe_python python3
if defined PYTHON_CMD goto :setup

echo ERROR: Python 3.12 or 3.13 x64 was not found.
echo Verify with: python --version
echo Verify architecture with: python -c "import struct; print(struct.calcsize('P')*8)"
pause
exit /b 1

:setup
echo Using Python command: %PYTHON_CMD%
%PYTHON_CMD% -c "import sys,struct; print(sys.version.split()[0], str(struct.calcsize('P')*8)+'-bit')"
if errorlevel 1 goto failed
%PYTHON_CMD% -m venv .venv
if errorlevel 1 goto failed
.venv\Scripts\python.exe -m pip install --only-binary=:all: -r requirements.txt
if errorlevel 1 goto failed
.venv\Scripts\python.exe -m unittest discover -s tests -v
if errorlevel 1 goto failed
echo.
echo Installation and offline self-tests succeeded.
pause
exit /b 0

:probe_python
%* -c "import sys,struct; sys.exit(0 if sys.version_info[:2] in ((3,12),(3,13)) and struct.calcsize('P') == 8 else 1)" >nul 2>&1
if not errorlevel 1 set "PYTHON_CMD=%*"
exit /b 0

:failed
echo ERROR: installation or tests failed.
pause
exit /b 1
