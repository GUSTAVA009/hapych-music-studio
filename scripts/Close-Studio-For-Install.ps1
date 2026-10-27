#Requires -Version 5.1
<#
Close only HAPYCH's own local Music Studio and ACE-Step services before an
installer changes their Python packages.

Safety:
 - Requires an exact command-line path match AND listener PID identity
 - Refuses to close any unknown program, even if it uses port 7862/7870
 - Never interrupts a Music Studio job in preparing/generating/converting
 - If only ACE-Step is running, asks before stopping it (its job state is
   unknown without Music Studio).
 - -CheckOnly reports state without terminating or prompting.
 - -NoPrompt fails safely when confirmation is needed.
 - Uses no wildcard Stop-Process, taskkill /IM or git reset.
#>
[CmdletBinding()]
param(
  [string]$Root,
  [int]$StudioPort=7870,
  [int]$EnginePort=7862,
  [switch]$CheckOnly,
  [switch]$NoPrompt,
  [switch]$AllowOrphanClose
)
$ErrorActionPreference='Stop'
if(-not $Root){$Root=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))}
$Root=[IO.Path]::GetFullPath($Root).TrimEnd('\')
if($StudioPort -eq $EnginePort -or $StudioPort -lt 1024 -or $EnginePort -lt 1024 -or
   $StudioPort -gt 65535 -or $EnginePort -gt 65535){
  throw 'Invalid Studio/ACE-Step port configuration'
}
$studioFile=Join-Path $Root 'app\studio_server.py'
$aceFile=Join-Path $Root 'ACE-Step-1.5\.venv\Scripts\acestep.exe'
foreach($requiredCommand in @('Get-NetTCPConnection','Get-CimInstance')){
  if(-not(Get-Command $requiredCommand -ErrorAction SilentlyContinue)){
    throw "Windows process inspection tool '$requiredCommand' is unavailable. Refusing unsafe shutdown."
  }
}

function Get-HapychPortOwners {
  param([int]$Port)
  # The listening socket's OwningProcess is authoritative. Do not search by
  # executable name alone (other users may also have python.exe running).
  $sockets=@(Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
  $owners=@($sockets | Where-Object {
      $_.LocalAddress -in @('127.0.0.1','::1','0.0.0.0','::')
    } | Select-Object -ExpandProperty OwningProcess -Unique)
  return @($owners)
}

function Test-LoopbackListener {
  param([int]$Port)
  foreach($hostName in @('127.0.0.1','::1')){
    $client=New-Object System.Net.Sockets.TcpClient
    try{
      $job=$client.BeginConnect($hostName,$Port,$null,$null)
      if($job.AsyncWaitHandle.WaitOne(500)){
        try{$client.EndConnect($job)}catch{}
        if($client.Connected){return $true}
      }
    }catch{}finally{$client.Close()}
  }
  return $false
}

function Get-HapychIdentity {
  param([int]$ProcessId,[int]$Port)
  $process=Get-CimInstance Win32_Process -Filter "ProcessId = $ProcessId" -ErrorAction SilentlyContinue
  if(-not $process){return $null}
  $exe=[string]$process.ExecutablePath
  $command=[string]$process.CommandLine
  $leaf=[IO.Path]::GetFileName($exe)
  # uv-managed Python on Windows is often python3.exe (not python.exe).
  # Accept only known Python launcher names; the exact HAPYCH script path
  # and listening-port ownership are still required independently below.
  if($leaf -notmatch '^(python(?:w)?(?:3(?:\.\d+)?)?|acestep)\.exe$'){return $null}
  $expected=if($Port -eq $StudioPort){$studioFile}else{$aceFile}
  $pattern='(?i)(?:^|["\s])'+[regex]::Escape($expected)+'(?=$|["\s])'
  if($command -notmatch $pattern){return $null}
  return [pscustomobject]@{
    Id=$ProcessId
    Port=$Port
    Role=if($Port -eq $StudioPort){'Music Studio'}else{'ACE-Step'}
  }
}

function Get-HapychServices {
  $found=@()
  foreach($port in @($StudioPort,$EnginePort)){
    foreach($ownerPid in @(Get-HapychPortOwners -Port $port)){
      if(-not $ownerPid){continue}
      $identity=Get-HapychIdentity -ProcessId ([int]$ownerPid) -Port $port
      if(-not $identity){
        throw ("Port $port is occupied by PID $ownerPid which is not a verified "+
               "HAPYCH Music Studio process. Refusing to close it. "+
               "Use Get-NetTCPConnection -LocalPort $port and Windows Task Manager "+
               "to identify the other program.")
      }
      $found+= $identity
    }
  }
  return @($found)
}

function Assert-HapychIdle {
  param([array]$Services)
  $studio=@($Services|Where-Object {$_.Port -eq $StudioPort})
  if(-not $studio.Count){return $false}
  try{
    $health=Invoke-RestMethod -Uri ("http://127.0.0.1:$StudioPort/api/health") -TimeoutSec 5
  }catch{
    throw 'Music Studio is running but its /api/health cannot be checked. '+
          'Will not interrupt an unknown generation; close Music Studio manually.'
  }
  if($health.name -ne 'Music Studio'){
    throw 'Port 7870 returned a different application. Refusing to terminate it.'
  }
  $status=[string]$health.job.status
  if($status -notin @('idle','done','error')){
    throw ("Music Studio has an active or unknown generation job (status='$status'). "+
           "Wait until the track completes before installing.")
  }
  Write-Host "Verified Music Studio job status: $status (safe to close)." -ForegroundColor Green
  return $true
}

function Confirm-OrphanACE {
  if($AllowOrphanClose){return $true}
  if($CheckOnly){return $false}
  if($NoPrompt){
    throw ('ACE-Step alone is running on port '+$EnginePort+
           '. Without Music Studio we cannot confirm it is idle. '+
           'Close ACE-Step manually or rerun Close-Studio-For-Install.ps1 -AllowOrphanClose.')
  }
  Write-Host 'ACE-Step is running without the Music Studio server.' -ForegroundColor Yellow
  Write-Host 'Its active-job state cannot be verified. Closing it might interrupt direct ACE-Step processing.' -ForegroundColor Yellow
  try{$answer=Read-Host 'Stop this verified local ACE-Step process so installation can continue? [Y/N]'}
  catch{throw 'Confirmation was unavailable. Close ACE-Step manually and rerun installation.'}
  if($answer -notmatch '^(?i:y|yes|д|да)$'){
    throw 'Installation paused without terminating ACE-Step. Finish or close its tasks before updating.'
  }
  return $true
}

function Stop-HapychService {
  param([object]$Service)
  # Recheck the socket owner and command line immediately before stopping to
  # minimize PID-reuse and cross-process risks.
  $owners=@(Get-HapychPortOwners -Port $Service.Port)
  if($owners -notcontains $Service.Id){
    throw "Port $($Service.Port) changed owner during installer shutdown; refusing."
  }
  if(-not(Get-HapychIdentity -ProcessId $Service.Id -Port $Service.Port)){
    throw "Process identity changed for PID $($Service.Id); refusing."
  }
  Write-Host ("Closing verified "+$Service.Role+" process PID "+$Service.Id+" ...") -ForegroundColor Yellow
  Stop-Process -Id $Service.Id -Force -ErrorAction Stop
}

$services=@(Get-HapychServices)
foreach($port in @($StudioPort,$EnginePort)){
  if(-not @($services |Where-Object {$_.Port -eq $port}).Count -and
     (Test-LoopbackListener -Port $port)){
    throw ("Local port "+$port+" is reachable but its listener PID cannot be "+
           "verified as HAPYCH-owned. Refusing to update a running or "+
           "unidentified service. Check Get-NetTCPConnection -LocalPort "+$port+".")
  }
}
if(-not $services.Count){
  Write-Host 'No Music Studio / ACE-Step listeners require shutdown.' -ForegroundColor Green
  exit 0
}
foreach($service in $services){
  Write-Host ("Detected owned "+$service.Role+" on port "+$service.Port+" (PID "+$service.Id+").") -ForegroundColor Yellow
}
if($CheckOnly){
  Write-Host 'CHECK_ONLY: no processes stopped or modified.' -ForegroundColor Green
  exit 0
}
$studioPresent=@($services|Where-Object {$_.Port -eq $StudioPort}).Count -gt 0
if($studioPresent){
  $null=Assert-HapychIdle -Services $services
}else{
  if(-not (Confirm-OrphanACE)){
    throw 'ACE-Step is still running; safe shutdown was not approved.'
  }
}
# Close front-end first to prevent new generation jobs; then terminate the
# owned ACE-Step engine which might outlive its parent Python process.
foreach($service in @($services|Sort-Object @{Expression={if($_.Port -eq $StudioPort){0}else{1}}})){
  Stop-HapychService -Service $service
}
for($i=0;$i -lt 45;$i++){
  Start-Sleep -Milliseconds 200
  $remaining=@(Get-HapychServices)
  if(-not $remaining.Count){
    Write-Host 'Studio and ACE-Step listeners stopped; safe to update Python environments.' -ForegroundColor Green
    exit 0
  }
}
throw 'Studio / ACE-Step still owns a port after shutdown. Stop the process manually before installing.'
