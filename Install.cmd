@echo off
setlocal
set "SETUP=%~dp0scripts\Bootstrap-Windows.ps1"
cd /d "%TEMP%"
echo.
echo   HAPYCH MUSIC STUDIO - WINDOWS INSTALLER
echo   This downloads third-party AI models and dependencies.
echo   Existing Music Studio folders and user recordings will not be overwritten.
echo.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%SETUP%" -Full -DownloadModels
if errorlevel 1 (
  echo.
  echo INSTALL FAILED. Read the error above. Nothing was deleted.
  pause
  exit /b 1
)
echo.
echo INSTALLATION COMPLETED.
pause
