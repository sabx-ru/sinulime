@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Run INSTALL.cmd first.
  pause
  exit /b 1
)
.venv\Scripts\python.exe -c "import snap7,importlib.metadata; print('python-snap7',importlib.metadata.version('python-snap7')); from snap7.type import Block; print('SDB support:',Block.SDB)"
if errorlevel 1 goto failed
.venv\Scripts\python.exe -m unittest discover -s tests -v
if errorlevel 1 goto failed
echo READY - this check does not connect to NCU.
pause
exit /b 0
:failed
echo FAILED. No NCU connection was attempted.
pause
exit /b 1
