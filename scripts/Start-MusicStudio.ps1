#Requires -Version 5.1
[CmdletBinding()]
param([switch]$NoBrowser)
$ErrorActionPreference='Stop'
$root=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$script=Join-Path $root 'app\studio_server.py'
$python=Join-Path $root 'ACE-Step-1.5\.venv\Scripts\python.exe'
$url='http://127.0.0.1:7870'
if(-not(Test-Path $script)){throw 'Music Studio server.py missing; clone this repository again.'}
if(-not(Test-Path $python)){throw 'ACE-Step Python missing. Run scripts\Install-Windows.ps1 first.'}
$env:NO_PROXY='127.0.0.1,localhost,::1'
$env:no_proxy=$env:NO_PROXY
$env:PYTHONUTF8='1'
function Is-Ready(){
  try{
    $r=Invoke-RestMethod -Uri ($url+'/api/health') -TimeoutSec 2
    return ($r.ready -eq $true)
  }catch{return $false}
}
if(-not(Is-Ready)){
  $app=Join-Path $root 'app'
  $stdout=Join-Path $app 'music-studio-stdout.log'
  $stderr=Join-Path $app 'music-studio-stderr.log'
  $args='-X utf8 "'+$script+'"'
  $p=Start-Process -FilePath $python -ArgumentList $args -WorkingDirectory $app -RedirectStandardOutput $stdout -RedirectStandardError $stderr -PassThru
  Write-Host "Starting Music Studio (PID $($p.Id))..." -ForegroundColor Cyan
  $success=$false
  for($i=0;$i -lt 90;$i++){
    if(Is-Ready){$success=$true;break}
    if($p.HasExited){break}
    Start-Sleep -Seconds 1
  }
  if(-not $success){throw "Server did not become ready. Inspect $stderr and $stdout"}
}
Write-Host "Music Studio is available at $url" -ForegroundColor Green
Write-Host 'ACE-Step models download / initialize on first generation.' -ForegroundColor DarkYellow
if(-not $NoBrowser){Start-Process $url}
