#Requires -Version 5.1
# End-to-end Windows integration: dummy HTTP Studio/ACE-Step processes running
# from a uniquely named TEMP folder, never the real user Music Studio.
# Uses random ephemeral ports and verifies PID ownership before any closure.
$ErrorActionPreference='Stop'
$helper=Join-Path (Split-Path $PSScriptRoot -Parent) 'scripts\Close-Studio-For-Install.ps1'
$workspace=Join-Path $env:TEMP ('hapych-install-stop-regression-'+[Guid]::NewGuid().ToString('N'))
$fakeRoot=Join-Path $workspace 'Music Studio With Spaces'
$studioScript=Join-Path $fakeRoot 'app\studio_server.py'
$aceScript=Join-Path $fakeRoot 'ACE-Step-1.5\.venv\Scripts\acestep.exe'
$statusFile=Join-Path $workspace 'job.txt'
$processes=@()
$python=(& uv python find 3.11).Trim()
if($LASTEXITCODE -ne 0 -or -not(Test-Path $python)){
  throw 'Python 3.11 must be installed via uv for this offline regression test'
}

$scriptCode=@'
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
import argparse, json
from pathlib import Path
p=argparse.ArgumentParser()
p.add_argument("--port",type=int,required=True)
p.add_argument("--job-file",type=str,required=True)
args=p.parse_args()
class Handler(BaseHTTPRequestHandler):
 def do_GET(self):
  status=Path(args.job_file).read_text(encoding="utf-8").strip()
  data={"name":"Music Studio","server_ready":True,"ready":False,"job":{"status":status}}
  raw=json.dumps(data).encode("utf-8")
  self.send_response(200)
  self.send_header("Content-Type","application/json")
  self.send_header("Content-Length",str(len(raw)))
  self.end_headers()
  self.wfile.write(raw)
 def log_message(self,*args): pass
ThreadingHTTPServer(("127.0.0.1",args.port),Handler).serve_forever()
'@

function Free-Port {
  $listener=New-Object Net.Sockets.TcpListener([Net.IPAddress]::Loopback,0)
  try{$listener.Start();return $listener.LocalEndpoint.Port}finally{$listener.Stop()}
}
function Run-Client([string]$file,[int]$port){
  $out=Join-Path $workspace ("run-$port.out")
  $err=Join-Path $workspace ("run-$port.err")
  $argList='-X utf8 "'+$file+'" --port '+$port+' --job-file "'+$statusFile+'"'
  $p=Start-Process -FilePath $python -ArgumentList $argList -PassThru -NoNewWindow -RedirectStandardOutput $out -RedirectStandardError $err
  $script:processes+= $p
  $ready=$false
  for($i=0;$i -lt 80;$i++){
    $owner=@(Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue |
             Where-Object {$_.OwningProcess -eq $p.Id -and $_.LocalAddress -eq '127.0.0.1'})
    if($owner.Count){$ready=$true;break}
    if($p.HasExited){break}
    Start-Sleep -Milliseconds 125
  }
  if(-not $ready){
    $details=if(Test-Path $err){Get-Content $err -Tail 20|Out-String}else{'no stderr'}
    throw ("Fixture process on $port failed to bind: "+$details)
  }
  return $p
}
function Invoke-Helper([string]$behavior,[int]$studio,[int]$ace){
  $out=Join-Path $workspace ("helper-"+$behavior+"-"+[Guid]::NewGuid().ToString('N')+".out")
  $err=Join-Path $workspace ("helper-"+$behavior+"-"+[Guid]::NewGuid().ToString('N')+".err")
  $argsList='-NoProfile -ExecutionPolicy Bypass -File "'+$helper+'" -Root "'+$fakeRoot+'" '
  $argsList+='-StudioPort '+$studio+' -EnginePort '+$ace+' -NoPrompt '
  if($behavior -eq 'check'){$argsList+='-CheckOnly'}
  if($behavior -eq 'orphan'){$argsList+='-AllowOrphanClose'}
  $process=Start-Process -FilePath powershell.exe -ArgumentList $argsList -Wait -PassThru -NoNewWindow -RedirectStandardOutput $out -RedirectStandardError $err
  return [pscustomobject]@{
    Exit=$process.ExitCode
    Output=@((Get-Content $out -ErrorAction SilentlyContinue)+(Get-Content $err -ErrorAction SilentlyContinue)) -join [Environment]::NewLine
  }
}
try{
  New-Item -ItemType Directory -Force -Path (Split-Path $studioScript -Parent),(Split-Path $aceScript -Parent)|Out-Null
  [IO.File]::WriteAllText($studioScript,$scriptCode,[Text.Encoding]::UTF8)
  [IO.File]::WriteAllText($aceScript,$scriptCode,[Text.Encoding]::UTF8)
  [IO.File]::WriteAllText($statusFile,"idle",[Text.Encoding]::UTF8)
  $studioPort=Free-Port
  $acePort=Free-Port
  if($studioPort -eq $acePort){$acePort=Free-Port}

  # Two owned listeners; the safe check does not touch either PID.
  $studio=Run-Client $studioScript $studioPort
  $ace=Run-Client $aceScript $acePort
  $check=Invoke-Helper check $studioPort $acePort
  if($check.Exit -ne 0 -or $check.Output -notmatch 'CHECK_ONLY'){
    throw ('Check-only failed: '+$check.Output)
  }
  if($studio.HasExited -or $ace.HasExited){throw 'Check-only accidentally stopped an active fixture'}
  Write-Host 'PASS: Fixture Studio and ACE-Step detected without stopping'

  # The server reports generating: no PID may be killed automatically.
  [IO.File]::WriteAllText($statusFile,"generating",[Text.Encoding]::UTF8)
  $busy=Invoke-Helper stop $studioPort $acePort
  if($busy.Exit -eq 0 -or $busy.Output -notmatch 'active or unknown generation'){
    throw ('Active job was not protected: '+$busy.Output)
  }
  if($studio.HasExited -or $ace.HasExited){throw 'In-flight music generation was interrupted'}
  Write-Host 'PASS: Active Studio generation is protected'

  # Idle Studio permits automatic close of BOTH matching listeners.
  [IO.File]::WriteAllText($statusFile,"idle",[Text.Encoding]::UTF8)
  $closed=Invoke-Helper stop $studioPort $acePort
  if($closed.Exit -ne 0 -or $closed.Output -notmatch 'safe to update'){
    throw ('Idle service stop failed: '+$closed.Output)
  }
  Start-Sleep -Milliseconds 350
  if(-not $studio.HasExited -or -not $ace.HasExited){throw 'Owned fixture processes survived shutdown'}
  Write-Host 'PASS: Verified idle Studio and ACE-Step both closed'

  # Orphan ACE-Step without a Studio server must require consent.
  $acePort=Free-Port
  $ace=Run-Client $aceScript $acePort
  $orphan=Invoke-Helper stop $studioPort $acePort
  if($orphan.Exit -eq 0 -or $orphan.Output -notmatch 'Without Music Studio'){
    throw ('Orphan ACE-Step was not guarded: '+$orphan.Output)
  }
  if($ace.HasExited){throw 'Orphan ACE-Step was stopped without consent'}
  $approved=Invoke-Helper orphan $studioPort $acePort
  if($approved.Exit -ne 0 -or $approved.Output -notmatch 'safe to update'){
    throw ('Explicitly approved orphan close failed: '+$approved.Output)
  }
  if(-not $ace.HasExited){throw 'Approved orphan remained running'}
  Write-Host 'PASS: Orphan ACE-Step cannot be closed non-interactively without explicit consent'

  # Foreign listener on the ACE-Step port must NEVER be stopped, even if
  # its executable is python.exe. Its CLI script path does not match.
  $foreign=Join-Path $workspace 'unrelated.py'
  [IO.File]::WriteAllText($foreign,$scriptCode,[Text.Encoding]::UTF8)
  $acePort=Free-Port
  $other=Run-Client $foreign $acePort
  $foreignTest=Invoke-Helper stop $studioPort $acePort
  if($foreignTest.Exit -eq 0 -or $foreignTest.Output -notmatch 'not a verified HAPYCH'){
    throw ('Foreign port process was not protected: '+$foreignTest.Output)
  }
  if($other.HasExited){throw 'Unrelated Python program was stopped'}
  Write-Host 'PASS: Foreign localhost service on ACE-Step port is never killed'
  Write-Host 'END_TO_END_SAFE_SHUTDOWN=PASS'
}finally{
  foreach($p in $processes){
    try{if(-not $p.HasExited){Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue}}catch{}
  }
  if(Test-Path $workspace){Remove-Item -LiteralPath $workspace -Force -Recurse -ErrorAction SilentlyContinue}
}
