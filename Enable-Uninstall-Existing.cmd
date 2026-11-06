@echo off
setlocal
set "HELPER=%~dp0scripts\Enable-Uninstall-Existing.ps1"
cd /d "%TEMP%"
echo.
echo HAPYCH MUSIC STUDIO - ENABLE UNINSTALL FOR EXISTING USERS
echo.
echo This does NOT reinstall models or remove songs.
echo It adds desktop/Start Menu shortcuts and Windows uninstall support.
echo.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%HELPER%"
if errorlevel 1 (
  echo.
  echo FAILED. Please review the message above.
  echo Your music and installed models were NOT intentionally removed.
  pause
  exit /b 1
)
echo.
echo DONE. Open Windows Settings - Installed apps - HAPYCH Music Studio.
pause
