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
  [switch]$ValidateOnly,
  [switch]$SyncOnly,
  [string]$TargetRoot
)
$ErrorActionPreference='Stop'
function Refresh-Path {
  $current=$env:Path
  $machine=[Environment]::GetEnvironmentVariable('Path','Machine')
  $user=[Environment]::GetEnvironmentVariable('Path','User')
  $extra=@(
    "$env:ProgramFiles\Git\cmd",
    "$env:LOCALAPPDATA\Programs\Git\cmd",
    "$env:USERPROFILE\.local\bin",
    "$env:LOCALAPPDATA\Microsoft\WinGet\Links"
  )
  # Must be idempotent: this helper is called repeatedly during setup.
  # Re-appending the entire system PATH on every call can exceed Windows'
  # process environment limit and make git/uv/FFmpeg mysteriously disappear.
  $seen=New-Object 'System.Collections.Generic.HashSet[string]' ([StringComparer]::OrdinalIgnoreCase)
  $parts=New-Object 'System.Collections.Generic.List[string]'
  foreach($part in (($current+';'+$machine+';'+$user+';'+($extra -join ';')) -split ';')){
    $clean=$part.Trim()
    if($clean -and $seen.Add($clean.TrimEnd('\'))){[void]$parts.Add($clean)}
  }
  $env:Path=($parts -join ';')
}
function Program-Found([string]$name) {
  Refresh-Path
  return [bool](Get-Command $name -ErrorAction SilentlyContinue)
}
if([Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT){
  throw 'HAPYCH Music Studio installer currently supports Windows 10/11 x64 only.'
}
$root=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..')).TrimEnd('\')
$target=if($TargetRoot){[IO.Path]::GetFullPath($TargetRoot).TrimEnd('\')}else{[IO.Path]::GetFullPath((Join-Path $HOME 'Music Studio')).TrimEnd('\')}
if($ValidateOnly){
  foreach($entry in @('scripts\Install-Windows.ps1','scripts\Verify-Install.ps1','app\studio_server.py','third_party_versions.json')){
    if(-not(Test-Path (Join-Path $root $entry))){throw "Incomplete ZIP or Git checkout: $entry"}
  }
  Write-Host '[PASS] Installer archive structure validated; no files moved or installed.' -ForegroundColor Green
  Write-Host "Source: $root"
  Write-Host "Target: $target"
  exit 0
}
# When launched from a newly extracted GitHub ZIP, reuse and update an
# existing official Git checkout instead of refusing to install. Never delete
# the target, replace personal tracks, or run git reset --hard.
if($SyncOnly -and $root -ieq $target){
  Write-Host '[PASS] Already in the installed Music Studio folder; sync-only requested, no changes made.' -ForegroundColor Green
  exit 0
}
if($root -ine $target){
  $targetExists=Test-Path -LiteralPath $target -PathType Container
  if($targetExists -and (Test-Path (Join-Path $target '.git'))){
    if(-not(Program-Found 'git')){
      throw "Git is needed to update the existing Music Studio. Install Git for Windows, then rerun Install.cmd."
    }
    $origin=(& git -C $target remote get-url origin).Trim()
    if($LASTEXITCODE -ne 0){throw "Cannot read Git origin from existing Music Studio. No files were changed."}
    $official=@(
      'https://github.com/GUSTAVA009/hapych-music-studio.git',
      'https://github.com/GUSTAVA009/hapych-music-studio',
      'git@github.com:GUSTAVA009/hapych-music-studio.git',
      'git@github.com:GUSTAVA009/hapych-music-studio'
    )
    if($official -notcontains $origin){
      throw "Existing Music Studio uses a different Git origin ($origin). Refusing to replace somebody else's project."
    }
    $branch=(& git -C $target symbolic-ref --quiet --short HEAD).Trim()
    if($LASTEXITCODE -ne 0 -or $branch -ne 'main'){
      throw "Existing Music Studio is not on the main branch. Switch to main safely before updating; no changes made."
    }
    $modified=@(& git -C $target status --porcelain --untracked-files=no)
    if($LASTEXITCODE -ne 0){throw 'Cannot inspect the existing Git checkout. No changes made.'}
    if($modified.Count){
      throw "Existing Music Studio has edited tracked files. Save or commit them first; automatic updates are blocked to protect your changes."
    }
    Write-Host "Official Music Studio already installed: $target" -ForegroundColor Cyan
    Write-Host 'Updating the Git source with fast-forward only. User songs/models will be preserved.' -ForegroundColor Cyan
    & git -C $target pull --ff-only origin main
    if($LASTEXITCODE -ne 0){throw 'Safe fast-forward Git update failed. Existing files were preserved.'}
    if($SyncOnly){
      Write-Host '[PASS] Existing Git installation updated without running model downloads.' -ForegroundColor Green
      exit 0
    }
  }elseif($targetExists){
    $existing=@(Get-ChildItem -LiteralPath $target -Force)
    if($existing.Count -eq 0){
      if($SyncOnly){throw "No Git repository exists at $target. Nothing to update."}
      Write-Host "Existing Music Studio folder is empty; copying source files without overwriting any data." -ForegroundColor Yellow
      Get-ChildItem -LiteralPath $root -Force | Copy-Item -Destination $target -Recurse -ErrorAction Stop
    }else{
      throw "Music Studio already contains files but is not a Git checkout: $target. No files were overwritten. Back up or rename this folder first, then rerun Install.cmd."
    }
  }else{
    if($SyncOnly){throw "No existing Music Studio Git repository at $target. Nothing to update."}
    Write-Host "Moving extracted GitHub ZIP to the required folder: $target" -ForegroundColor Cyan
    Move-Item -LiteralPath $root -Destination $target -ErrorAction Stop
  }
  # The target is now the up-to-date source tree, not the ZIP on Desktop.
  $next=Join-Path $target 'scripts\Bootstrap-Windows.ps1'
  if(-not(Test-Path $next)){throw 'Music Studio Git update did not produce the expected Bootstrap script.'}
  $argsList=@('-NoProfile','-ExecutionPolicy','Bypass','-File',$next)
  if($Full){$argsList+='-Full'}
  if($DownloadModels){$argsList+='-DownloadModels'}
  if($NoPrerequisites){$argsList+='-NoPrerequisites'}
  if($NoLaunch){$argsList+='-NoLaunch'}
  if($TargetRoot){$argsList+=@('-TargetRoot',$target)}
  & powershell.exe @argsList
  if($LASTEXITCODE -ne 0){throw "Music Studio installation failed after preparing the target (exit $LASTEXITCODE). User data was not deleted."}
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
# For brand-new installs, protect users from running out of disk mid-download.
# For a *repeat* install, do not demand 20 GiB if most models are cached.
$mainCached=Test-Path (Join-Path $target 'ACE-Step-1.5\checkpoints\acestep-v15-turbo')
$voiceCached=(Test-Path (Join-Path $target 'Voice Engine\alternatives\ApexSVC\checkpoints\WavLM-Large.pt')) -and
             (Test-Path (Join-Path $target 'Voice Engine\alternatives\ApexSVC\checkpoints\G_150k.pt'))
if($Full -or $DownloadModels){
  if($mainCached -and $voiceCached){$min=3GB}
  elseif($mainCached){$min=10GB}
  else{$min=20GB}
}else{
  $min=if($mainCached){2GB}else{8GB}
}
Write-Host ('Free disk space: {0:N1} GiB; minimum for this install state: {1:N0} GiB' -f ($free/1GB),($min/1GB))
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
