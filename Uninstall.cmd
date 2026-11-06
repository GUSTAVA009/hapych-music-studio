@echo off
setlocal
cd /d "%~dp0"
echo.
echo HAPYCH MUSIC STUDIO - REMOVE FROM WINDOWS
echo Personal songs and voice recordings are preserved by option 1.
echo Do not close this window until uninstall finishes.
echo.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\Uninstall-Windows.ps1"
if errorlevel 1 (
  echo.
  echo UNINSTALL FAILED. Read the error above. Nothing else will be deleted.
  pause
  exit /b 1
)
echo.
pause
