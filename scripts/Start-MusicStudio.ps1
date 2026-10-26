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
function Is-ServerAlive(){
  try{
    $r=Invoke-RestMethod -Uri ($url+'/api/health') -TimeoutSec 3
    # The HTTP app can be healthy while ACE-Step still downloads its models.
    return ($r.server_ready -eq $true -or $r.name -eq 'Music Studio')
  }catch{return $false}
}
function Is-PortOccupied(){
  $client=New-Object System.Net.Sockets.TcpClient
  try{
    $job=$client.BeginConnect('127.0.0.1',7870,$null,$null)
    if(-not $job.AsyncWaitHandle.WaitOne(1200)){return $false}
    $client.EndConnect($job)
    return $client.Connected
  }catch{return $false}finally{$client.Close()}
}
if(-not(Is-ServerAlive)){
  if(Is-PortOccupied){throw 'Port 7870 is already occupied, but /api/health is unavailable. Do not launch a duplicate server. Run scripts\Diagnose-Windows.ps1 and check the process holding port 7870.'}
  $app=Join-Path $root 'app'
  $stdout=Join-Path $app 'music-studio-stdout.log'
  $stderr=Join-Path $app 'music-studio-stderr.log'
  $args='-X utf8 "'+$script+'"'
  $p=Start-Process -FilePath $python -ArgumentList $args -WorkingDirectory $app -RedirectStandardOutput $stdout -RedirectStandardError $stderr -PassThru
  Write-Host "Starting Music Studio (PID $($p.Id))..." -ForegroundColor Cyan
  $success=$false
  for($i=0;$i -lt 90;$i++){
    if(Is-ServerAlive){$success=$true;break}
    if($p.HasExited){break}
    Start-Sleep -Seconds 1
  }
  if(-not $success){throw "Server did not become ready. Inspect $stderr and $stdout"}
}
Write-Host "Music Studio web server is available at $url" -ForegroundColor Green
try{
  $h=Invoke-RestMethod -Uri ($url+'/api/health') -TimeoutSec 4
  $engineLabel=if($h.engine){$h.engine.message}else{'ACE-Step loading / model download may still be in progress'}
  Write-Host "ACE-Step: $engineLabel" -ForegroundColor Yellow
}catch{Write-Host 'ACE-Step status unavailable; try scripts\Diagnose-Windows.ps1' -ForegroundColor Yellow}
Write-Host 'Note: web-server availability is NOT proof that music models are initialized.' -ForegroundColor DarkYellow
if(-not $NoBrowser){Start-Process $url}
