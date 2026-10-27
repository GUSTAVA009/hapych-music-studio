#Requires -Version 5.1
[CmdletBinding()]
param(
 [switch]$VoiceOnly,
 [switch]$RebuildVoiceEnvironment,
 [switch]$DownloadModels,
 [switch]$CheckOnly
)
$ErrorActionPreference='Stop'
$root=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$voice=Join-Path $root 'Voice Engine'
$venv=Join-Path $voice '.venv'
$py=Join-Path $venv 'Scripts\python.exe'
$guard=Join-Path $root 'tools\verify_voice_runtime.py'
$logDir=Join-Path $root 'Install Logs'
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$log=Join-Path $logDir ('repair-'+(Get-Date -Format 'yyyyMMdd-HHmmss')+'.log')
function Say([string]$message) { Write-Host $message; Add-Content -LiteralPath $log -Value $message -Encoding UTF8 }
function VoiceHealthy {
 if(-not(Test-Path -LiteralPath $py -PathType Leaf)){return $false}
 if(-not(Test-Path -LiteralPath $guard -PathType Leaf)){return $false}
 try { & $py -X utf8 $guard 2>&1 | Out-String | Add-Content -LiteralPath $log -Encoding UTF8; return ($LASTEXITCODE -eq 0) }
 catch {return $false}
}
$healthy=VoiceHealthy
Say ('Voice environment healthy: '+$healthy)
if($CheckOnly){ Say ('Log: '+$log); if($healthy){exit 0}else{exit 2} }
# Never touch a running studio or voice job; the installer handles safe shutdown.
if((Test-Path -LiteralPath $venv) -and ($RebuildVoiceEnvironment -or -not $healthy)){
 $running=@(Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {
  $_.CommandLine -and $_.CommandLine.Contains($venv) -and $_.ProcessId -ne $PID
 })
 if($running.Count){throw 'Voice environment is in use. Stop active jobs before recovery.'}
 $backup=Join-Path $voice ('.venv.incomplete.'+(Get-Date -Format 'yyyyMMdd-HHmmss'))
 if(Test-Path -LiteralPath $backup){throw 'Recovery backup already exists.'}
 Rename-Item -LiteralPath $venv -NewName ([IO.Path]::GetFileName($backup))
 Say ('Old voice environment preserved as: '+$backup)
}
$installer=Join-Path $root 'scripts\Install-Windows.ps1'
if(-not(Test-Path -LiteralPath $installer)){throw 'Installer is missing: '+$installer}
Say 'Repairing the full dependency graph; personal tracks and voice profiles are untouched.'
# The current installer is idempotent and installs the common music stack
# before the full voice engine, even if only voice recovery was requested.
$argsList=@('-NoProfile','-ExecutionPolicy','Bypass','-File',$installer,'-Full')
if($DownloadModels){$argsList+='-DownloadModels'}
& powershell.exe @argsList 2>&1 | Tee-Object -FilePath $log -Append
if($LASTEXITCODE -ne 0){throw 'Installation did not finish. See log: '+$log}
$verify=Join-Path $root 'scripts\Verify-Install.ps1'
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $verify -CheckVoice
if($LASTEXITCODE -ne 0){throw 'Post-install voice verification failed. See log: '+$log}
if(-not(VoiceHealthy)){throw 'Voice imports failed after installation. See log: '+$log}
Say ('PASS: repaired runtime and verified imports. Log: '+$log)
Say 'Voice model inference must still be tested separately.'
