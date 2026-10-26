#Requires -Version 5.1
[CmdletBinding()]
param([switch]$CheckVoice)
$ErrorActionPreference='Continue'
$root=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$errors=New-Object System.Collections.Generic.List[string]
function Check-File([string]$part){
  $p=Join-Path $root $part
  if(Test-Path $p){Write-Host "[OK] $part" -ForegroundColor Green}
  else{$errors.Add("Missing: $part");Write-Host "[MISSING] $part" -ForegroundColor Red}
}
Check-File 'app\studio_server.py'
Check-File 'app\ui\index.html'
Check-File 'ACE-Step-1.5\.venv\Scripts\python.exe'
Check-File 'ACE-Step-1.5\.venv\Scripts\acestep.exe'
if($CheckVoice){
  Check-File 'Voice Engine\.venv\Scripts\python.exe'
  Check-File 'Voice Engine\seed-vc\inference_studio75.py'
  Check-File 'Voice Engine\alternatives\ApexSVC\.venv\Scripts\python.exe'
  Check-File 'Voice Engine\alternatives\ApexSVC\svc\pipeline.py'
}
$python=Join-Path $root 'ACE-Step-1.5\.venv\Scripts\python.exe'
if(Test-Path $python){
  & $python -X utf8 -m compileall -q (Join-Path $root 'app')
  if($LASTEXITCODE -eq 0){Write-Host '[OK] Python app syntax' -ForegroundColor Green}
  else{$errors.Add('Python compilation failed')}
  & $python -X utf8 -c "import requests, gradio_client, numpy, soundfile; print('[OK] Core Python imports')"
  if($LASTEXITCODE -ne 0){$errors.Add('Core Python imports failed')}
}
if(-not(Get-Command ffmpeg -ErrorAction SilentlyContinue)){$errors.Add('ffmpeg is not on PATH')}
if($errors.Count){
  Write-Host 'Installation is not complete:' -ForegroundColor Yellow
  foreach($e in $errors){Write-Host (' - '+$e)}
  exit 1
}
Write-Host 'Local source and installed dependencies passed lightweight checks.' -ForegroundColor Green
Write-Host 'This does not download/verify model weights or test generated audio.'
exit 0
