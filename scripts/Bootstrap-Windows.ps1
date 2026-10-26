#Requires -Version 5.1
<#
Public Windows bootstrap for Git clone OR GitHub "Download ZIP".
One-click path: extract the whole ZIP, double-click Install.cmd.
Never deletes an existing Music Studio or personal data.
#>
[CmdletBinding()]
param(
  [switch]$Full,
  [switch]$DownloadModels,
  [switch]$NoPrerequisites,
  [switch]$NoLaunch,
  [switch]$ValidateOnly
)
$ErrorActionPreference='Stop'
function Refresh-Path {
  $machine=[Environment]::GetEnvironmentVariable('Path','Machine')
  $user=[Environment]::GetEnvironmentVariable('Path','User')
  $extra=@(
    "$env:ProgramFiles\Git\cmd",
    "$env:LOCALAPPDATA\Programs\Git\cmd",
    "$env:USERPROFILE\.local\bin",
    "$env:LOCALAPPDATA\Microsoft\WinGet\Links"
  )
  $env:Path=($machine+';'+$user+';'+($extra -join ';'))
}
function Program-Found([string]$name) {
  Refresh-Path
  return [bool](Get-Command $name -ErrorAction SilentlyContinue)
}
if([Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT){
  throw 'HAPYCH Music Studio installer currently supports Windows 10/11 x64 only.'
}
$root=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..')).TrimEnd('\')
$target=[IO.Path]::GetFullPath((Join-Path $HOME 'Music Studio')).TrimEnd('\')
if($ValidateOnly){
  foreach($entry in @('scripts\Install-Windows.ps1','scripts\Verify-Install.ps1','app\studio_server.py','third_party_versions.json')){
    if(-not(Test-Path (Join-Path $root $entry))){throw "Incomplete ZIP or Git checkout: $entry"}
  }
  Write-Host '[PASS] Installer archive structure validated; no files moved or installed.' -ForegroundColor Green
  Write-Host "Source: $root"
  Write-Host "Target: $target"
  exit 0
}
if($root -ine $target){
  if(Test-Path -LiteralPath $target){
    throw "Music Studio already exists at '$target'. To protect data, the installer will not overwrite it. Run this project's setup from that folder instead."
  }
  Write-Host "Moving extracted GitHub ZIP to the required folder: $target" -ForegroundColor Cyan
  Move-Item -LiteralPath $root -Destination $target -ErrorAction Stop
  $next=Join-Path $target 'scripts\Bootstrap-Windows.ps1'
  $argsList=@('-NoProfile','-ExecutionPolicy','Bypass','-File',$next)
  if($Full){$argsList+='-Full'}
  if($DownloadModels){$argsList+='-DownloadModels'}
  if($NoPrerequisites){$argsList+='-NoPrerequisites'}
  if($NoLaunch){$argsList+='-NoLaunch'}
  & powershell.exe @argsList
  if($LASTEXITCODE -ne 0){throw "Bootstrap after folder move failed (exit $LASTEXITCODE)"}
  exit 0
}
$needed=@(
  @{exe='git';id='Git.Git';url='https://git-scm.com/download/win'},
  @{exe='uv';id='astral-sh.uv';url='https://docs.astral.sh/uv/getting-started/installation/'},
  @{exe='ffmpeg';id='Gyan.FFmpeg';url='https://ffmpeg.org/download.html'}
)
$missing=@($needed|Where-Object {-not (Program-Found $_.exe)})
if($missing.Count){
  if($NoPrerequisites){
    throw ('Missing tools: '+(($missing|ForEach-Object{$_.exe}) -join ', ')+'. Install them first.')
  }
  if(-not(Program-Found 'winget')){
    Write-Host 'winget is missing. Install missing tools manually:' -ForegroundColor Yellow
    foreach($entry in $missing){Write-Host "  $($entry.exe): $($entry.url)"}
    throw 'Git, uv and FFmpeg are required. Windows App Installer/winget is unavailable.'
  }
  foreach($entry in $missing){
    Write-Host "Installing $($entry.exe) via Windows Package Manager..." -ForegroundColor Cyan
    & winget install --id $entry.id --exact --source winget --accept-source-agreements --accept-package-agreements --disable-interactivity
    if($LASTEXITCODE -ne 0 -and -not(Program-Found $entry.exe)){
      throw "Installation of $($entry.exe) failed; try the official site: $($entry.url)"
    }
    if(-not(Program-Found $entry.exe)){
      throw "$($entry.exe) was installed but still is not in PATH. Open a new PowerShell and rerun Install.cmd."
    }
  }
}
$disk=[IO.Path]::GetPathRoot($target)
$free=(New-Object System.IO.DriveInfo($disk)).AvailableFreeSpace
$min=if($Full -or $DownloadModels){20GB}else{8GB}
if($free -lt $min){
  throw ("Insufficient free space on {0}: {1:N1} GiB free; at least {2:N0} GiB required before downloading models." -f $disk,($free/1GB),($min/1GB))
}
$install=Join-Path $target 'scripts\Install-Windows.ps1'
$verify=Join-Path $target 'scripts\Verify-Install.ps1'
$launch=Join-Path $target 'scripts\Start-MusicStudio.ps1'
foreach($p in @($install,$verify,$launch)){
  if(-not(Test-Path $p)){throw "Incomplete archive (missing $p). Download ZIP again."}
}
$opts=@('-NoProfile','-ExecutionPolicy','Bypass','-File',$install)
if($Full){$opts+='-Full'}
if($DownloadModels){$opts+='-DownloadModels'}
Write-Host 'Installing HAPYCH Music Studio; this may download many GB of pretrained models.' -ForegroundColor Cyan
& powershell.exe @opts
if($LASTEXITCODE -ne 0){throw "Music Studio install failed with exit $LASTEXITCODE. Existing data was not deleted."}
$test=@('-NoProfile','-ExecutionPolicy','Bypass','-File',$verify)
if($Full){$test+='-CheckVoice'}
if($DownloadModels){$test+='-CheckModels'}
& powershell.exe @test
if($LASTEXITCODE -ne 0){throw "Installation verification failed (exit $LASTEXITCODE)"}
Write-Host 'Installation finished. User data and model caches remain in the local folder.' -ForegroundColor Green
if(-not $NoLaunch){
  & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $launch
  if($LASTEXITCODE -ne 0){throw 'Music Studio could not start. See app startup log.'}
}
