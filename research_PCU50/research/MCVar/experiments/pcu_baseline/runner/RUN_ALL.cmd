@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0"
set "SESSION_ID=%RANDOM%_%RANDOM%"
set "LOG=logs\RUN_ALL_%SESSION_ID%.txt"
set "STOP=0"
set "SYSTEM_ERRORS=0"
set "STEPS=0"
set "RESULT_OK=0"
set "RESULT_NEG=0"
set "RESULT_OTHER=0"
if not exist "logs" mkdir "logs"
if not exist "bin\pcu_watchdog.exe" goto MISSING
if not exist "bin\mcvar_multiread.exe" goto MISSING
if not exist "bin\dde_series.exe" goto MISSING
if not exist "config\items_control.txt" goto MISSING
if exist "STOP_TESTS.flag" goto STOP_PRESENT
>"%LOG%" echo PowerLine integrated test suite 2026-10-31
>>"%LOG%" echo Started %DATE% %TIME%; session=%SESSION_ID%
echo PowerLine integrated read-only tests. No interactive prompts.
echo Session log: %LOG%
echo Raw captures and software diagnostics: bin\logs\
echo STOP_TESTS.flag skips pending tests. Child watchdog limits each EXE run.
if exist "%SystemRoot%\system32\tasklist.exe" tasklist /v >"logs\TASKLIST_BEFORE_%SESSION_ID%.txt" 2>nul

echo === A_COM_API_BASELINE ===
>>"%LOG%" echo PHASE A_COM_API_BASELINE %DATE% %TIME%
call :META "A00_METADATA"
call :MC "A01_BATCH_01" "config\items_control.txt" "--limit=1 --shape=array-bstr --cache-device=1" "OK"
call :MC "A02_BATCH_02" "config\items_control.txt" "--limit=2 --shape=array-bstr --cache-device=1" "OK"
call :MC "A03_BATCH_03" "config\items_control.txt" "--limit=3 --shape=array-bstr --cache-device=1" "OK"
call :MC "A04_BATCH_05" "config\items_control.txt" "--limit=5 --shape=array-bstr --cache-device=1" "OK"
call :MC "A05_BATCH_07" "config\items_control.txt" "--limit=7 --shape=array-bstr --cache-device=1" "OK"
call :MC "A06_BATCH_10" "config\items_control.txt" "--limit=10 --shape=array-bstr --cache-device=1" "OK"
call :MC "A07_BATCH_15" "config\items_control.txt" "--limit=15 --shape=array-bstr --cache-device=1" "OK"
call :MC "A08_BATCH_20" "config\items_control.txt" "--limit=20 --shape=array-bstr --cache-device=1" "OK"
call :MC "A09_SCALAR" "config\items_1.txt" "--limit=1 --shape=scalar --cache-device=1" "OK"
call :MC "A10_LOWERBOUND_1" "config\items_control.txt" "--limit=1 --shape=array-bstr --lower-bound=1 --cache-device=1" "OK"
call :MC "A11_LOWERBOUND_5" "config\items_control.txt" "--limit=5 --shape=array-bstr --lower-bound=1 --cache-device=1" "OK"
call :MC "A12_LOWERBOUND_20" "config\items_control.txt" "--limit=20 --shape=array-bstr --lower-bound=1 --cache-device=1" "OK"
call :MC "A13_REPEAT_20" "config\items_control.txt" "--limit=20 --shape=array-bstr --repeat=2 --interval-ms=2500 --cache-device=1" "OK"

echo === B_ORDER_DUPLICATES_NONATOMICITY ===
>>"%LOG%" echo PHASE B_ORDER_DUPLICATES_NONATOMICITY %DATE% %TIME%
call :MC "B01_REVERSE_5" "config\items_control.txt" "--limit=5 --reverse --shape=array-bstr --cache-device=1" "OK"
call :MC "B02_REVERSE_20" "config\items_control.txt" "--limit=20 --reverse --shape=array-bstr --cache-device=1" "OK"
call :MC "B03_DUPLICATE_LAST_20" "config\items_control.txt" "--limit=20 --duplicate-last --shape=array-bstr --cache-device=1" "OK"
call :MC "B04_DUPLICATE_MIX" "config\duplicate5.txt" "--limit=5 --shape=array-bstr --cache-device=1" "OK"
call :MC "B05_STATIC_20" "config\static20.txt" "--limit=20 --shape=array-bstr --cache-device=1" "OK"
call :MC "B06_CLOCK_20" "config\clock20.txt" "--limit=20 --shape=array-bstr --cache-device=1" "OK"
call :MC "B07_CLOCK_20_REPEAT" "config\clock20.txt" "--limit=20 --shape=array-bstr --repeat=2 --interval-ms=3000 --cache-device=1" "OK"
call :MC "B08_DYN_MIX_20" "config\dyn_interleaved20.txt" "--limit=20 --shape=array-bstr --cache-device=1" "OK"
call :MC "B09_STRINGS_5" "config\strings5.txt" "--limit=5 --shape=array-bstr --cache-device=1" "OK"
call :MC "B10_DOUBLES_5" "config\doubles5.txt" "--limit=5 --shape=array-bstr --cache-device=1" "OK"
call :MC "B11_INTS_5" "config\integer5.txt" "--limit=5 --shape=array-bstr --cache-device=1" "OK"
call :MC "B12_DOMAINS_5" "config\domain5.txt" "--limit=5 --shape=array-bstr --cache-device=1" "OK"
call :MC "B13_R_INDICES_5" "config\r_indices5.txt" "--limit=5 --shape=array-bstr --cache-device=1" "ANY"
call :MC "B14_CLOCK_AND_R" "config\clock_and_params5.txt" "--limit=5 --shape=array-bstr --cache-device=1" "ANY"

echo === C_ERROR_HRESULT_RECOVERY ===
>>"%LOG%" echo PHASE C_ERROR_HRESULT_RECOVERY %DATE% %TIME%
call :MC "C01_ONE_BAD_FIRST" "config\items_control.txt" "--limit=5 --invalid-first --shape=array-bstr --cache-device=1" "ANY"
call :MC "C02_ONE_BAD_MIDDLE" "config\items_control.txt" "--limit=5 --invalid-middle --shape=array-bstr --cache-device=1" "ANY"
call :MC "C03_ONE_BAD_LAST" "config\items_control.txt" "--limit=5 --invalid-last --shape=array-bstr --cache-device=1" "ANY"
call :MC "C04_BAD_TWO" "config\bad2mixed5.txt" "--limit=5 --shape=array-bstr --cache-device=1" "ANY"
call :MC "C05_ALL_BAD" "config\bad3only.txt" "--limit=3 --shape=array-bstr --cache-device=1" "NEG"
call :MC "C06_BAD20_SPARSE" "config\bad20spread.txt" "--limit=20 --shape=array-bstr --cache-device=1" "ANY"
call :MC "C07_DUP_BAD5" "config\bad5same.txt" "--limit=5 --shape=array-bstr --cache-device=1" "NEG"
call :MC "C08_UNSUPPORTED_VARIANT" "config\items_1.txt" "--limit=1 --shape=array-variant --cache-device=1" "NEG"
call :MC "C09_RECOVER_AFTER_ERR" "config\items_control.txt" "--limit=20 --shape=array-bstr --cache-device=1" "OK"

echo === D_CACHEDEVICE_FRESHNESS ===
>>"%LOG%" echo PHASE D_CACHEDEVICE_FRESHNESS %DATE% %TIME%
call :MC "D01_CACHE_STATIC_1" "config\items_1.txt" "--limit=1 --shape=array-bstr --cache-device=1" "OK"
call :MC "D02_CACHE_STATIC_0" "config\items_1.txt" "--limit=1 --shape=array-bstr --cache-device=0" "OK"
call :MC "D03_CACHE_STATIC_2" "config\items_1.txt" "--limit=1 --shape=array-bstr --cache-device=2" "OK"
call :MC "D04_CACHE_STATIC_1" "config\items_1.txt" "--limit=1 --shape=array-bstr --cache-device=1" "OK"
call :MC "D05_CACHE_CLOCK_1" "config\clock1.txt" "--limit=1 --shape=array-bstr --repeat=2 --interval-ms=3000 --cache-device=1" "OK"
call :MC "D06_CACHE_CLOCK_0" "config\clock1.txt" "--limit=1 --shape=array-bstr --repeat=2 --interval-ms=3000 --cache-device=0" "OK"
call :MC "D07_CACHE_CLOCK_2" "config\clock1.txt" "--limit=1 --shape=array-bstr --repeat=2 --interval-ms=3000 --cache-device=2" "OK"
call :MC "D08_CACHE_CLOCK_1" "config\clock1.txt" "--limit=1 --shape=array-bstr --repeat=2 --interval-ms=3000 --cache-device=1" "OK"
call :MC "D11_CACHE_CLOCK20_0" "config\clock20.txt" "--limit=20 --shape=array-bstr --cache-device=0" "OK"
call :MC "D12_CACHE_CLOCK20_1" "config\clock20.txt" "--limit=20 --shape=array-bstr --cache-device=1" "OK"
call :MC "D13_CACHE_CLOCK20_2" "config\clock20.txt" "--limit=20 --shape=array-bstr --cache-device=2" "OK"

echo === E_DIRECT_DDE_BINARY_FORMATS ===
>>"%LOG%" echo PHASE E_DIRECT_DDE_BINARY_FORMATS %DATE% %TIME%
call :DDE "E01_BINARY_ONE" "config\items_1.txt" 1 binary 1 text-first OK 35000
call :DDE "E02_TEXT_ONLY_FIVE" "config\items_5.txt" 5 text 1 text-first OK 35000
call :DDE "E03_BINARY_ONE_AFTER_TEXT" "config\items_1.txt" 1 binary 1 text-first OK 35000
call :DDE "E04_BINARY_TWENTY" "config\items_control.txt" 20 binary 1 text-first OK 68000
call :DDE "E05_BOTH_5_TEXT_FIRST" "config\items_5.txt" 5 both 1 text-first OK 43000
call :DDE "E06_BOTH_5_BINARY_FIRST" "config\items_5.txt" 5 both 1 binary-first OK 43000
call :DDE "E07_REPEAT_BINARY_1" "config\items_1.txt" 1 binary 2 text-first OK 35000
call :DDE "E08_REPEAT_BINARY_5" "config\items_5.txt" 5 binary 2 text-first OK 43000
call :DDE "E09_REPEAT_MIXED_5" "config\items_5.txt" 5 both 2 binary-first OK 68000
call :DDE "E10_DDE_STRINGS" "config\strings5.txt" 5 both 1 text-first OK 43000
call :DDE "E11_DDE_DOUBLES" "config\doubles5.txt" 5 binary 1 text-first OK 35000
call :DDE "E12_DDE_INTS" "config\integer5.txt" 5 binary 1 text-first OK 35000
call :DDE "E13_DDE_DOMAINS" "config\domain5.txt" 5 both 1 text-first OK 43000
call :DDE "E14_DDE_CLOCK5" "config\clock5.txt" 5 binary 1 text-first OK 35000
call :DDE "E15_DDE_STATIC5" "config\static20.txt" 20 binary 1 text-first OK 68000
call :DDE "E16_DDE_REVERSE20" "config\reverse20.txt" 20 binary 1 text-first OK 68000
call :DDE "E17_DDE_R_INDICES" "config\r_indices5.txt" 5 binary 1 text-first ANY 35000

echo === F_OEMTEXT_AND_REGISTERED_FORMAT ===
>>"%LOG%" echo PHASE F_OEMTEXT_AND_REGISTERED_FORMAT %DATE% %TIME%
call :DDE "F01_OEM_ONE" "config\items_1.txt" 1 oem 1 text-first ANY 35000
call :DDE "F02_OEM_FIVE" "config\items_5.txt" 5 oem 1 text-first ANY 35000
call :DDE "F03_ALL_FORMATS_1" "config\items_1.txt" 1 all 1 text-first ANY 35000
call :DDE "F04_ALL_FORMATS_5" "config\items_5.txt" 5 all 1 text-first ANY 55500
call :DDE "F05_ALL_BINARY_FIRST" "config\items_5.txt" 5 all 1 binary-first ANY 55500
call :DDE "F06_OEM_BAD" "config\bad_middle3.txt" 3 oem 1 text-first ANY 35000
call :DDE "F07_ALL_BAD_MIX" "config\bad_middle3.txt" 3 all 1 text-first ANY 40500

echo === G_COUNTER_BRIDGES_MCVAR_TO_NCDDE ===
>>"%LOG%" echo PHASE G_COUNTER_BRIDGES_MCVAR_TO_NCDDE %DATE% %TIME%
call :DDE "G00_BEFORE_1" "config\items_1.txt" 1 binary 1 text-first OK 35000
call :MC "G01_MC_1" "config\items_1.txt" "--limit=1 --shape=array-bstr --cache-device=1" "OK"
call :DDE "G02_AFTER_MC1" "config\items_1.txt" 1 binary 1 text-first OK 35000
call :MC "G03_MC_5" "config\items_control.txt" "--limit=5 --shape=array-bstr --cache-device=1" "OK"
call :DDE "G04_AFTER_MC5" "config\items_1.txt" 1 binary 1 text-first OK 35000
call :MC "G05_MC_20" "config\items_control.txt" "--limit=20 --shape=array-bstr --cache-device=1" "OK"
call :DDE "G06_AFTER_MC20" "config\items_1.txt" 1 binary 1 text-first OK 35000
call :MC "G07_MC_5_BAD2" "config\bad2mixed5.txt" "--limit=5 --shape=array-bstr --cache-device=1" "ANY"
call :DDE "G08_AFTER_BAD2" "config\items_1.txt" 1 binary 1 text-first OK 35000
call :MC "G09_MC_ALL_BAD" "config\bad3only.txt" "--limit=3 --shape=array-bstr --cache-device=1" "NEG"
call :DDE "G10_AFTER_ALL_BAD" "config\items_1.txt" 1 binary 1 text-first OK 35000
call :MC "G11_MC_BAD_SHAPE" "config\items_1.txt" "--limit=1 --shape=array-variant --cache-device=1" "NEG"
call :DDE "G12_AFTER_BAD_SHAPE" "config\items_1.txt" 1 binary 1 text-first OK 35000
call :DDE "G13_TEXT_ONLY" "config\items_5.txt" 5 text 1 text-first OK 35000
call :DDE "G14_AFTER_TEXT" "config\items_1.txt" 1 binary 1 text-first OK 35000
call :DDE "G15_DDE_BAD" "config\bad3only.txt" 3 binary 1 text-first NEG 35000
call :DDE "G16_AFTER_DDE_BAD" "config\items_1.txt" 1 binary 1 text-first OK 35000
call :MC "G17_MCV_20_REPEAT2" "config\items_control.txt" "--limit=20 --repeat=2 --interval-ms=2500 --shape=array-bstr --cache-device=1" "OK"
call :DDE "G18_AFTER_40" "config\items_1.txt" 1 binary 1 text-first OK 35000

echo === H_FAILURE_RECOVERY_AND_BINARY_BOUNDARIES ===
>>"%LOG%" echo PHASE H_FAILURE_RECOVERY_AND_BINARY_BOUNDARIES %DATE% %TIME%
call :DDE "H01_DDE_BAD_FIRST" "config\bad_first3.txt" 3 both 1 text-first NEG 35000
call :DDE "H02_DDE_BAD_MIDDLE" "config\bad_middle3.txt" 3 both 1 text-first NEG 35000
call :DDE "H03_DDE_BAD_LAST" "config\bad_last3.txt" 3 both 1 text-first NEG 35000
call :DDE "H04_DDE_ALL_BAD" "config\bad3only.txt" 3 both 1 text-first NEG 35000
call :DDE "H05_DDE_RECOVERY" "config\items_5.txt" 5 both 1 text-first OK 43000
call :MC "H06_MC_RECOVERY" "config\items_control.txt" "--limit=20 --shape=array-bstr --cache-device=1" "OK"
call :DDE "H07_SPINDLE_VALUES" "config\spindle5.txt" 5 both 1 text-first OK 43000
call :DDE "H08_CLOCK_MIXED" "config\clock_and_params5.txt" 5 binary 1 text-first ANY 35000

echo === I_FINAL_REPLICATION ===
>>"%LOG%" echo PHASE I_FINAL_REPLICATION %DATE% %TIME%
call :MC "I01_MC20" "config\items_control.txt" "--limit=20 --shape=array-bstr --cache-device=1" "OK"
call :DDE "I02_DDE20" "config\items_control.txt" 20 binary 1 text-first OK 68000
call :MC "I03_CLOCK20" "config\clock20.txt" "--limit=20 --repeat=2 --interval-ms=3000 --shape=array-bstr --cache-device=1" "OK"
call :DDE "I04_DDE_CLOCK5" "config\clock5.txt" 5 binary 2 text-first OK 43000
call :DDE "I05_COUNTER_END" "config\items_1.txt" 1 binary 1 text-first OK 35000
goto FINISH
:META
call :GUARD
if "%STOP%"=="1" exit /b 0
set /a STEPS+=1
echo [%STEPS%] %~1
>>"%LOG%" echo START %STEPS% META %~1 %DATE% %TIME%
bin\pcu_watchdog.exe --timeout-ms=45000 -- bin\mcvar_multiread.exe --metadata >"logs\console_%SESSION_ID%_%~1.txt" 2>&1
set "RC=%ERRORLEVEL%"
call :REC "%~1" "META" "OK"
exit /b 0
:MC
call :GUARD
if "%STOP%"=="1" exit /b 0
set /a STEPS+=1
echo [%STEPS%] MCVar %~1
>>"%LOG%" echo START %STEPS% MC %~1 %DATE% %TIME%
bin\pcu_watchdog.exe --timeout-ms=90000 -- bin\mcvar_multiread.exe --read --confirm=YES --items="%~2" %~3 >"logs\console_%SESSION_ID%_%~1.txt" 2>&1
set "RC=%ERRORLEVEL%"
call :REC "%~1" "MC" "%~4"
exit /b 0
:DDE
call :GUARD
if "%STOP%"=="1" exit /b 0
set /a STEPS+=1
echo [%STEPS%] DDE %~1
>>"%LOG%" echo START %STEPS% DDE %~1 %DATE% %TIME%
bin\pcu_watchdog.exe --timeout-ms=%~8 -- bin\dde_series.exe --confirm=YES --items="%~2" --expect-items=%~3 --mode=%~4 --rounds=%~5 --order=%~6 --interval-ms=1500 --timeout-ms=5000 >"logs\console_%SESSION_ID%_%~1.txt" 2>&1
set "RC=%ERRORLEVEL%"
call :REC "%~1" "DDE" "%~7"
exit /b 0
:GUARD
if exist "STOP_TESTS.flag" set "STOP=1"
exit /b 0
:REC
set "STATUS=REVIEW"
if "%RC%"=="0" set "STATUS=OK"
if "%RC%"=="20" set "STATUS=RESPONDED"
if "%RC%"=="10" set "STATUS=API_NEGATIVE"
if "%RC%"=="21" set "STATUS=ITEM_FAILURE"
if "%RC%"=="90" set "STATUS=TIMEOUT"
if "%RC%"=="91" set "STATUS=CREATE_FAILURE"
if "%RC%"=="92" set "STATUS=WAIT_FAILURE"
if "%RC%"=="93" set "STATUS=CLI_FAILURE"
if "%RC%"=="89" set "STATUS=CHILD_EXIT_OVER_79"
echo %~1 RC=%RC% status=%STATUS%
>>"%LOG%" echo END %STEPS% %~2 %~1 RC=%RC% status=%STATUS% expect=%~3 %DATE% %TIME%
if "%RC%"=="0" goto REC_OK
if "%RC%"=="20" goto REC_OK
if "%RC%"=="10" goto REC_EXPECTED
if "%RC%"=="21" goto REC_EXPECTED
set /a SYSTEM_ERRORS+=1
set /a RESULT_OTHER+=1
if "%RC%"=="90" set "STOP=1"
if %SYSTEM_ERRORS% GEQ 2 set "STOP=1"
goto REC_WAIT
:REC_OK
set /a RESULT_OK+=1
goto REC_WAIT
:REC_EXPECTED
set /a RESULT_NEG+=1
:REC_WAIT
rem Deliberate inter-process pause between tests (WinXP built-in ping).
ping -n 3 127.0.0.1 >nul
exit /b 0
:FINISH
if exist "%SystemRoot%\system32\tasklist.exe" tasklist /v >"logs\TASKLIST_AFTER_%SESSION_ID%.txt" 2>nul
echo FINISH total=%STEPS% answered=%RESULT_OK% negatives=%RESULT_NEG% others=%RESULT_OTHER% stopped=%STOP%
>>"%LOG%" echo FINISH total=%STEPS% answered=%RESULT_OK% negatives=%RESULT_NEG% others=%RESULT_OTHER% stopped=%STOP% %DATE% %TIME%
echo Keep the complete logs\ and bin\logs\ folders for analysis.
if "%STOP%"=="1" exit /b 1
exit /b 0
:MISSING
echo ERROR: First run build_debian.sh on Debian, then transfer the full folder to the PCU.
exit /b 2
:STOP_PRESENT
echo ERROR: STOP_TESTS.flag exists. Remove it before a new run.
exit /b 3
