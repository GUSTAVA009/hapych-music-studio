@echo off
setlocal
cd /d "%~dp0"
echo HAPYCH MUSIC STUDIO - INSTALLATION RECOVERY
echo Repairs incomplete voice dependencies and downloads missing public models.
echo Your music, voice recordings and trained models are preserved.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\Repair-Windows.ps1" -VoiceOnly -DownloadModels
if errorlevel 1 (
 echo REPAIR FAILED. Check Install Logs in the installation folder.
 pause
 exit /b 1
)
echo Recovery checks completed. Test voice conversion in Music Studio.
pause
