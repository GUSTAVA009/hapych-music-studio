#Requires -Version 5.1
<#
Read-only HAPYCH Music Studio diagnostic for end-user computers.
No music generation, no modification of user libraries or AI models.
Reports environment, connectivity, selected model files and safe error summaries.
The report is saved only on the user's PC, NEVER uploaded automatically.
#>
[CmdletBinding()]
param([switch]$CheckApi,[switch]$OpenReport)
$ErrorActionPreference='Continue'
$root=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$timestamp=Get-Date -Format 'yyyyMMdd-HHmmss'
$report=Join-Path $env:TEMP ("HAPYCH-MusicStudio-Diagnostics-"+$timestamp+".txt")
$lines=New-Object 'System.Collections.Generic.List[string]'
function Clean([object]$value){
  $txt=[string]$value
  $txt=$txt -replace '(?i)C:\\Users\\[^\\]+','C:\Users\<USER>'
  $txt=$txt -replace '(?i)(github_pat_[A-Za-z0-9_]+|gh[pousr]_[A-Za-z0-9]+)','[REDACTED_TOKEN]'
  $txt=$txt -replace '(?i)(sk-[A-Za-z0-9_-]{24,})','[REDACTED_TOKEN]'
  $txt=$txt -replace '(?i)(Bearer\s+[A-Za-z0-9._-]{12,})','[REDACTED_TOKEN]'
  return ($txt -replace '[\r\n]+',' ').Trim()
}
function Note([string]$line){
  $safe=Clean $line
  Write-Host $safe
  $lines.Add($safe)
}
function Has([string]$rel){
  $f=Join-Path $root $rel
  Note ("FILE "+$rel+" = "+(Test-Path -LiteralPath $f))
}
function Test-HTTP([string]$url,[switch]$Full){
  try{
    if($Full){
      $body=Invoke-RestMethod -Uri $url -TimeoutSec 7 -ErrorAction Stop
      Note ("HTTP "+$url+" = OK")
      return $body
    }
    $response=Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 7 -ErrorAction Stop
    Note ("HTTP "+$url+" = "+$response.StatusCode)
  }catch{
    Note ("HTTP "+$url+" = FAILED: "+(Clean $_.Exception.Message))
  }
  return $null
}
Note ("HAPYCH MUSIC STUDIO DIAGNOSTIC "+(Get-Date -Format 's'))
Note "This report is LOCAL; no file is uploaded."
Note ("OS = "+[Environment]::OSVersion.VersionString)
Note ("Is64Bit = "+[Environment]::Is64BitOperatingSystem)
try{
  $os=Get-CimInstance Win32_OperatingSystem -ErrorAction Stop
  Note ("Physical RAM (GiB) = "+[math]::Round($os.TotalVisibleMemorySize/1MB,2))
  Note ("Free RAM (GiB) = "+[math]::Round($os.FreePhysicalMemory/1MB,2))
}catch{Note "RAM_INFO = unavailable"}
try{
  $rootDrive=[IO.Path]::GetPathRoot($root)
  $disk=New-Object System.IO.DriveInfo($rootDrive)
  Note ("Disk free (GiB) = "+[math]::Round($disk.AvailableFreeSpace/1GB,2))
}catch{Note "DISK_INFO = unavailable"}
try{
  foreach($gpu in (Get-CimInstance Win32_VideoController -ErrorAction Stop)){
    Note ("Video adapter = "+$gpu.Name)
  }
}catch{Note "VIDEO_ADAPTERS = unavailable"}
foreach($tool in @('git','uv','ffmpeg','ffprobe','nvidia-smi')){
  $cmd=Get-Command $tool -ErrorAction SilentlyContinue
  if(-not $cmd){Note ("COMMAND "+$tool+" = MISSING");continue}
  Note ("COMMAND "+$tool+" = present")
  if($tool -eq 'nvidia-smi'){
    try{
      $gpuStatus=@(& nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader 2>$null)
      foreach($gpu in $gpuStatus){Note ("NVIDIA_GPU = "+$gpu)}
    }catch{}
  }
}
if(Test-Path (Join-Path $root '.git')){
  try{
    $head=(& git -C $root rev-parse --short HEAD 2>$null)
    Note ("App Git revision = "+$head)
  }catch{Note "APP_REVISION = unknown"}
}else{Note "APP_REVISION = ZIP install / no .git folder"}
foreach($file in @(
 'app\studio_server.py',
 'app\ui\studio42.js',
 'ACE-Step-1.5\pyproject.toml',
 'ACE-Step-1.5\.venv\Scripts\python.exe',
 'ACE-Step-1.5\.venv\Scripts\acestep.exe',
 'Voice Engine\.venv\Scripts\python.exe',
 'Voice Engine\alternatives\ApexSVC\.venv\Scripts\python.exe'
)){Has $file}
$python=Join-Path $root 'ACE-Step-1.5\.venv\Scripts\python.exe'
if(Test-Path $python){
  try{
    $pyStatus=@(& $python -X utf8 -c "import sys; print('Python:',sys.version.split()[0]); import torch;print('PyTorch:',torch.__version__);print('CUDA available:',torch.cuda.is_available());print('GPU count:',torch.cuda.device_count())" 2>&1)
    foreach($line in $pyStatus|Select-Object -Last 8){Note ("PYTHON "+$line)}
  }catch{Note ("PYTHON_PROBE_ERROR = "+(Clean $_.Exception.Message))}
}
Note "--- Local server / AI engine connectivity ---"
$health=Test-HTTP 'http://127.0.0.1:7870/api/health' -Full
if($null -ne $health){
  Note ("WEB_SERVER_READY = "+$health.server_ready)
  Note ("ENGINE_ENDPOINT_RESPONDING = "+$health.ready)
  if($health.engine){
    Note ("ENGINE_STATUS = "+$health.engine.status)
    Note ("ENGINE_MESSAGE = "+$health.engine.message)
    Note ("ENGINE_PROCESS_ALIVE = "+$health.engine.process_alive)
  }
  if($health.job){
    Note ("LAST_JOB_STATUS = "+$health.job.status)
    if($health.job.status -eq 'error'){
      Note ("LAST_JOB_ERROR = "+$health.job.error)
    }
  }
}
$diagnostics=Test-HTTP 'http://127.0.0.1:7870/api/diagnostics' -Full
if($null -ne $diagnostics){
  Note ("API_GENERATOR_INSTALLED = "+$diagnostics.generator_installed)
}
Test-HTTP 'http://127.0.0.1:7862/config' |Out-Null
if($CheckApi -and $null -ne $health){
  Note "--- Testing harmless /api/prepare (no music generation) ---"
  $request=@{title='Diagnostic test';style='Ambient instrumental, piano and light drums, calm, 100 BPM'
             lyrics='[Instrumental]';instrumental=$true;duration=30;bpm=100;mode='new';use_voice=$false}
  try{
    $json=$request|ConvertTo-Json -Compress
    $data=Invoke-RestMethod -Uri 'http://127.0.0.1:7870/api/prepare' -Method Post -ContentType 'application/json; charset=utf-8' -Body ([Text.Encoding]::UTF8.GetBytes($json)) -TimeoutSec 22 -ErrorAction Stop
    Note ("API_PREPARE = SUCCESS, caption length "+([string]$data.caption).Length)
  }catch{
    Note ("API_PREPARE = FAILED: "+(Clean $_.Exception.Message))
    try{
      if($_.ErrorDetails.Message){
        Note ("API_ERROR = "+(Clean $_.ErrorDetails.Message).Substring(0,[math]::Min(360,(Clean $_.ErrorDetails.Message).Length)))
      }
    }catch{}
  }
}
Note "--- Recent diagnostic error patterns from LOCAL logs ---"
$pattern='(?i)(Traceback|Exception|ModuleNotFound|ImportError|cuda out of memory|outofmemory|no CUDA|model.+not found|FileNotFound|connection refused|port.+in use|Failed to fetch|invalid|fatal|error initializing|error loading|error:|runtimeerror|python.+failed)'
foreach($name in @('app\music-studio-stderr.log','app\music-studio-stdout.log',
                    'app\studio-server.log','Music Studio.log')){
  $log=Join-Path $root $name
  if(-not(Test-Path -LiteralPath $log)){continue}
  try{
    $hits=@(Get-Content -LiteralPath $log -Tail 600 -Encoding UTF8 -ErrorAction Stop|Where-Object {$_ -match $pattern}|Select-Object -Last 11)
    Note ("LOG "+$name+" (matched lines: "+$hits.Count+")")
    foreach($hit in $hits){Note ("   "+(Clean $hit).Substring(0,[math]::Min(300,(Clean $hit).Length)))}
  }catch{Note ("LOG "+$name+" cannot be read")}
}
Note "--- End of report ---"
$lines|Set-Content -LiteralPath $report -Encoding UTF8
Write-Host ("Report saved on this computer: "+$report) -ForegroundColor Green
Write-Host "Inspect the report before sharing. Do not send personal WAV, passwords or full logs."
if($OpenReport){Start-Process -FilePath notepad.exe -ArgumentList @($report)}
