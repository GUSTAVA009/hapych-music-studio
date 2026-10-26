@echo off
setlocal
set "DOCTOR=%~dp0scripts\Diagnose-Windows.ps1"
cd /d "%TEMP%"
echo.
echo HAPYCH MUSIC STUDIO - READ-ONLY DIAGNOSTIC
echo The report remains on this computer. No user audio is uploaded.
echo.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%DOCTOR%" -CheckApi -OpenReport
if errorlevel 1 (
  echo.
  echo Diagnostic failed. Copy the error above without your private data.
)
pause
