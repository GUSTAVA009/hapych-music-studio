#Requires -Version 5.1
[CmdletBinding()]
param([switch]$CheckVoice,[switch]$CheckModels,[switch]$Smoke)
$ErrorActionPreference='Stop'
$root=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$checks=Join-Path $root 'tools\verify_install.py'
$py=Join-Path $root 'ACE-Step-1.5\.venv\Scripts\python.exe'
$errors=New-Object 'System.Collections.Generic.List[string]'
function Warn([string]$msg){Write-Host "[WARN] $msg" -ForegroundColor Yellow}
function Test-Required([string]$p){
  if(-not(Test-Path $p)){$errors.Add("Missing: $p");Write-Host "[FAIL] $p" -ForegroundColor Red}
  else{Write-Host "[OK] $p" -ForegroundColor Green}
}
Test-Required $checks
Test-Required $py
foreach($exe in @('git','uv','ffmpeg','ffprobe')){
  if(-not(Get-Command $exe -ErrorAction SilentlyContinue)){$errors.Add("Command '$exe' not found on PATH")}
}
if(Test-Path $py){
  $argsList=@('-X','utf8',$checks,'--root',$root)
  if($CheckVoice){$argsList+='--voice'}
  if($CheckModels){$argsList+='--models'}
  Write-Host "Checking source, dependencies and pinned external engines..." -ForegroundColor Cyan
  & $py @argsList
  if($LASTEXITCODE -ne 0){$errors.Add("Python component verification failed (exit $LASTEXITCODE)")}
  $parserArgs=@('-X','utf8','-m','compileall','-q',
    (Join-Path $root 'app'),
    (Join-Path $root 'Voice Engine'),
    (Join-Path $root 'tools'))
  & $py @parserArgs
  if($LASTEXITCODE -ne 0){$errors.Add("Python source compilation failed")}
}
if($Smoke -and $errors.Count -eq 0){
  Write-Host 'Testing the localhost web server...' -ForegroundColor Cyan
  $launch=Join-Path $root 'scripts\Start-MusicStudio.ps1'
  & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $launch -NoBrowser
  if($LASTEXITCODE -ne 0){$errors.Add('Web server did not launch')}
  else{
    try{
      $health=Invoke-RestMethod 'http://127.0.0.1:7870/api/health' -TimeoutSec 9
      if(-not ($health.server_ready -or $health.name -eq 'Music Studio')){
        $errors.Add('Web server does not respond with a valid Music Studio health result')
      }else{
        Write-Host '[OK] Music Studio web server responds.' -ForegroundColor Green
        if(-not $health.ready){
          Warn 'ACE-Step is not ready yet. Model initialization/download is separate from the web server.'
          if($health.engine){Warn $health.engine.message}
        }
      }
    }catch{$errors.Add('Cannot query local Music Studio health endpoint')}
  }
}
if($errors.Count){
  Write-Host 'Installation verification failed:' -ForegroundColor Red
  foreach($message in $errors){Write-Host " - $message"}
  exit 1
}
Write-Host 'PASS: Files, dependencies and selected model checks completed.' -ForegroundColor Green
if(-not $CheckModels){Warn 'Model download NOT verified; use -CheckModels after -DownloadModels.'}
Warn 'Speech quality, vocal likeness and actual end-to-end audio generation have not been verified by this test.'
exit 0
