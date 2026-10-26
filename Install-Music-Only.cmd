@echo off
setlocal
set "SETUP=%~dp0scripts\Bootstrap-Windows.ps1"
cd /d "%TEMP%"
echo.
echo HAPYCH MUSIC STUDIO - MUSIC ONLY SETUP (WITHOUT OPTIONAL VOICE MODELS)
echo.
echo This installs ACE-Step, Music Studio and main music models.
echo You can upgrade later to the full voice package with Install.cmd.
echo Existing tracks and microphone files are not deleted.
echo.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%SETUP%" -DownloadModels
if errorlevel 1 (
  echo.
  echo Installation stopped. Read the error above. You can safely retry.
  pause
  exit /b 1
)
echo.
echo MUSIC STUDIO MAIN INSTALLATION COMPLETED.
pause
