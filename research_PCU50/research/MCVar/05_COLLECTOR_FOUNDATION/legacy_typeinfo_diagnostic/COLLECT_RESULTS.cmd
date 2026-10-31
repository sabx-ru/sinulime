@echo off
setlocal
cd /d "%~dp0"
if not exist results.jsonl if not exist results_async.jsonl if not exist results_cyclic.jsonl (
  echo No results JSONL files found.
  exit /b 2
)
for %%F in (results*.jsonl) do if exist "%%F" copy /y "%%F" "%~dp0collected_%%F" >nul
echo Collected result files in %CD%
