#Requires -Version 5.1
<#
Safe, interactive uninstaller. No admin rights, no deletion without confirmation.
Mode KeepData: move personal content to Documents backup, then delete this app and its models.
Mode DeleteAll: remove everything after a second explicit confirmation.
The installer-created marker and canonical installation path protect unrelated folders.
#>
[CmdletBinding()]
param(
  [string]$Root = (Join-Path $HOME 'Music Studio'),
  [ValidateSet('Prompt','KeepData','DeleteAll')][string]$Mode = 'Prompt',
  [switch]$TestMode,
  [string]$ProgramsDir,
  [string]$DesktopDir,
  [string]$RegistryPath,
  [string]$BackupRoot
)
$ErrorActionPreference = 'Stop'
if ([Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT) { throw 'Windows required.' }
$rootPath = [IO.Path]::GetFullPath($Root).TrimEnd('\')
$expected = [IO.Path]::GetFullPath((Join-Path $HOME 'Music Studio')).TrimEnd('\')
if (-not $TestMode -and $rootPath -ine $expected) {
  throw "Unexpected install location. Refusing to delete: $rootPath"
}
if (-not(Test-Path -LiteralPath $rootPath -PathType Container)) { throw 'Installation folder does not exist.' }
$markerPath = Join-Path $rootPath '.hapych-installed.json'
if (-not(Test-Path -LiteralPath $markerPath -PathType Leaf)) {
  throw 'Install safety marker is missing. Nothing was removed. Reinstall/repair from the official archive first.'
}
$marker = Get-Content -LiteralPath $markerPath -Raw -Encoding UTF8 | ConvertFrom-Json
if ($marker.product -ne 'HAPYCH Music Studio' -or [string]$marker.installRoot -ine $rootPath -or $marker.schema -ne 1) {
  throw 'Install safety marker does not match this folder. Nothing was removed.'
}
if (-not $ProgramsDir) { $ProgramsDir = Join-Path ([Environment]::GetFolderPath('Programs')) 'HAPYCH Music Studio' }
if (-not $DesktopDir) { $DesktopDir = [Environment]::GetFolderPath('DesktopDirectory') }
if (-not $RegistryPath) { $RegistryPath = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\HAPYCHMusicStudio' }
if (-not $BackupRoot) {
  $BackupRoot = Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'HAPYCH Music Studio Backups'
}
if ($TestMode -and $RegistryPath -notlike 'HKCU:\Software\HAPYCH-Installer-Tests\*') {
  throw 'TestMode requires an isolated HKCU test registry path.'
}
$installedReg = Get-ItemProperty -LiteralPath $RegistryPath -ErrorAction SilentlyContinue
if ($installedReg -and [string]$installedReg.InstallLocation -ine $rootPath) {
  throw 'Windows registration points to another folder. Nothing was removed.'
}
Write-Host 'HAPYCH Music Studio / Uninstall' -ForegroundColor Cyan
Write-Host "Installed at: $rootPath"
if ($Mode -eq 'Prompt') {
  Write-Host '1 - Uninstall application and downloaded models; SAVE songs, recordings and profiles to Documents.'
  Write-Host '2 - DELETE EVERYTHING including personal recordings, profiles, songs and models.'
  Write-Host '0 - Cancel.'
  $choice = (Read-Host 'Enter 1, 2 or 0').Trim()
  if ($choice -eq '1') { $Mode = 'KeepData' }
  elseif ($choice -eq '2') { $Mode = 'DeleteAll' }
  else { Write-Host 'Cancelled. Nothing was removed.'; exit 0 }
}
if (-not $TestMode) {
  $answer = Read-Host "Type UNINSTALL to confirm deletion of $rootPath"
  if ($answer -cne 'UNINSTALL') { Write-Host 'Cancelled. Nothing was removed.'; exit 0 }
  if ($Mode -eq 'DeleteAll') {
    $danger = Read-Host 'All personal music and voice files will be destroyed. Type DELETE ALL'
    if ($danger -cne 'DELETE ALL') { Write-Host 'Cancelled. Nothing was removed.'; exit 0 }
  }
}
# Reject junctions and symbolic links before recursively deleting: never follow a
# link outside the installation folder. Affected users should remove links manually.
if (Test-Path -LiteralPath (Join-Path $rootPath '.git') -PathType Container) {
  $git = Get-Command git -ErrorAction SilentlyContinue
  if (-not $git) { throw 'Git is required to check for local source changes before uninstall.' }
  $changed = @(& git -C $rootPath status --porcelain=v1 --untracked-files=no)
  if ($LASTEXITCODE -ne 0) { throw 'Cannot inspect local source changes. Nothing was removed.' }
  if ($changed.Count -gt 0) { throw 'Locally modified source files detected. Save/export your edits before uninstall. Nothing was removed.' }
}
$links = @(Get-ChildItem -LiteralPath $rootPath -Force -Recurse -ErrorAction Stop |
  Where-Object { ($_.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0 })
if ($links.Count -gt 0) {
  throw "Reparse points inside the installation: $($links[0].FullName). Refusing to delete."
}
if (-not $TestMode) {
  $stop = Join-Path $rootPath 'scripts\Close-Studio-For-Install.ps1'
  if (-not(Test-Path -LiteralPath $stop)) { throw 'Safe shutdown helper missing. Nothing was removed.' }
  & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $stop -Root $rootPath
  if ($LASTEXITCODE -ne 0) { throw 'A Music Studio/ACE-Step task is running or shutdown was refused. Nothing was removed.' }
}
$backup = ''
if ($Mode -eq 'KeepData') {
  $backup = Join-Path $BackupRoot ((Get-Date -Format 'yyyyMMdd-HHmmss') + '-' + [Guid]::NewGuid().ToString('N').Substring(0,8))
  New-Item -ItemType Directory -Path $backup -Force | Out-Null
  function Save-Entry([string]$entry) {
    $from = Join-Path $rootPath $entry
    if (-not(Test-Path -LiteralPath $from)) { return }
    $to = Join-Path $backup $entry
    $parent = Split-Path $to -Parent
    New-Item -ItemType Directory -Path $parent -Force | Out-Null
    if (Test-Path -LiteralPath $to) { throw "Backup collision: $to" }
    Move-Item -LiteralPath $from -Destination $to -ErrorAction Stop
  }
  # Personal folders created by the installer and popular additional content folders.
  $personal = @('Мой голос','Мои треки','Исходные версии','Мастер WAV',
    'Voice Profiles','Integrations','Exports','Sound Library','Training Runs',
    'Install Logs','presets','research','My Music','My Voice')
  foreach ($entry in $personal) { Save-Entry $entry }
  # Preserve unknown top-level files and folders, not just known song locations.
  $owned = @('.git','.github','.gitattributes','.gitignore','.hapych-installed.json',
    'ACE-Step-1.5','Voice Engine','app','Text Engine','overlays','requirements',
    'scripts','tools','docs','tests','legacy-launchers','Music Studio.ico',
    'README.md','LICENSE','third_party_versions.json','Install.cmd',
    'Install-Music-Only.cmd','Repair-Install.cmd','Diagnose.cmd','Uninstall.cmd')
  foreach ($item in @(Get-ChildItem -LiteralPath $rootPath -Force)) {
    if ($owned -notcontains $item.Name) { Save-Entry $item.Name }
  }
  # Also preserve audio and personal configuration saved under application-owned
  # folders, since earlier versions may have written exports in unexpected places.
  $extensions = @('.wav','.mp3','.flac','.ogg','.m4a','.opus','.aiff','.aif','.mid','.midi',
    '.sqlite','.sqlite3','.db','.csv','.xlsx','.xls','.docx','.txt','.env',
    '.json','.yaml','.yml','.toml')
  foreach ($rel in @('app','Voice Engine','Text Engine')) {
    $folder = Join-Path $rootPath $rel
    if (-not(Test-Path -LiteralPath $folder -PathType Container)) { continue }
    foreach ($file in @(Get-ChildItem -LiteralPath $folder -File -Recurse -Force -ErrorAction Stop)) {
      if ($extensions -notcontains $file.Extension.ToLowerInvariant()) { continue }
      # Do not save bulk third-party model examples or dependencies as personal songs.
      $relative = $file.FullName.Substring($rootPath.Length).TrimStart('\')
      if ($relative -match '^Voice Engine\\(seed-vc|alternatives\\ApexSVC|\.venv)(\\|$)') { continue }
      Save-Entry $relative
    }
  }
  Write-Host "Your saved data was moved to: $backup" -ForegroundColor Green
}
# Only a stamped, exact Music Studio folder can reach this line.
# Model/dependency directories may be large; any deletion failure is reported.
Remove-Item -LiteralPath $rootPath -Recurse -Force -ErrorAction Stop
if (Test-Path -LiteralPath $RegistryPath) { Remove-Item -LiteralPath $RegistryPath -Force -ErrorAction Stop }
foreach ($link in @(
  (Join-Path $ProgramsDir 'HAPYCH Music Studio.lnk'),
  (Join-Path $ProgramsDir 'Uninstall HAPYCH Music Studio.lnk'),
  (Join-Path $DesktopDir 'HAPYCH Music Studio.lnk'))) {
  if (Test-Path -LiteralPath $link -PathType Leaf) {
    $shell = New-Object -ComObject WScript.Shell
    $shortcut = $shell.CreateShortcut($link)
    if ([string]$shortcut.WorkingDirectory -ieq $rootPath) {
      Remove-Item -LiteralPath $link -Force
    }
  }
}
if ((Test-Path -LiteralPath $ProgramsDir) -and @(Get-ChildItem -LiteralPath $ProgramsDir -Force).Count -eq 0) {
  Remove-Item -LiteralPath $ProgramsDir -Force
}
Write-Host '[PASS] HAPYCH Music Studio removed from Windows.' -ForegroundColor Green
if ($backup) { Write-Host "Personal files backup: $backup" -ForegroundColor Green }
Write-Host 'Shared packages (Git, uv, FFmpeg) were not uninstalled because other apps may need them.'
