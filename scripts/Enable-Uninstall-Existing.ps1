#Requires -Version 5.1
<#
Upgrade an already-installed HAPYCH Music Studio with Windows uninstall support.
No AI model install, application launch, personal media upload or deletion.
The expected production target is %USERPROFILE%\Music Studio.
#>
[CmdletBinding()]
param(
  [string]$TargetRoot = (Join-Path $HOME 'Music Studio'),
  [switch]$TestMode,
  [string]$ProgramsDir,
  [string]$DesktopDir,
  [string]$RegistryPath
)
$ErrorActionPreference = 'Stop'
if ([Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT) { throw 'Windows 10/11 required.' }
$source = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..')).TrimEnd('\')
$target = [IO.Path]::GetFullPath($TargetRoot).TrimEnd('\')
$expected = [IO.Path]::GetFullPath((Join-Path $HOME 'Music Studio')).TrimEnd('\')
if (-not $TestMode -and $target -ine $expected) {
  throw "Refusing to modify any other folder: $target"
}
if ($TestMode -and ($RegistryPath -notlike 'HKCU:\Software\HAPYCH-Installer-Tests\*' -or
    -not $ProgramsDir -or -not $DesktopDir)) {
  throw 'TestMode needs isolated Start Menu, Desktop and registry paths.'
}
if (-not (Test-Path -LiteralPath $target -PathType Container)) {
  throw "Installed Music Studio directory not found: $target"
}
if ((Get-Item -LiteralPath $target -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) {
  throw 'Installation folder is a symbolic link/junction. Refusing to modify it.'
}
foreach ($f in @('app\studio_server.py','scripts\Start-MusicStudio.ps1','third_party_versions.json')) {
  if (-not (Test-Path -LiteralPath (Join-Path $target $f) -PathType Leaf)) {
    throw "Folder does not match an installed Music Studio: missing $f"
  }
}
if (-not $RegistryPath) {
  $RegistryPath = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\HAPYCHMusicStudio'
}
$registered = Get-ItemProperty -Path $RegistryPath -ErrorAction SilentlyContinue
if ($registered -and [string]$registered.InstallLocation -ine $target) {
  throw 'Windows already has a different HAPYCH Music Studio installation registered.'
}
$markerPath = Join-Path $target '.hapych-installed.json'
if (Test-Path -LiteralPath $markerPath -PathType Leaf) {
  $marker = Get-Content -LiteralPath $markerPath -Raw -Encoding UTF8 | ConvertFrom-Json
  if ($marker.product -ne 'HAPYCH Music Studio' -or
      [string]$marker.installRoot -ine $target -or $marker.schema -ne 1) {
    throw 'Existing installation marker does not match this folder. Nothing was changed.'
  }
}
$files = @('scripts\Register-Windows.ps1','scripts\Uninstall-Windows.ps1',
           'Uninstall.cmd','Music Studio.ico')
foreach ($f in $files) {
  if (-not (Test-Path -LiteralPath (Join-Path $source $f) -PathType Leaf)) {
    throw "The downloaded archive is incomplete: $f"
  }
}
if ($source -ine $target) {
  if (Test-Path -LiteralPath (Join-Path $target '.git') -PathType Container) {
    if ($TestMode) { throw 'Git updates must not run in the disposable TestMode.' }
    if (-not (Get-Command git -ErrorAction SilentlyContinue)) { throw 'Git is required for an existing Git checkout.' }
    $origin = (& git -C $target remote get-url origin).Trim()
    $allowed = @('https://github.com/GUSTAVA009/hapych-music-studio.git',
      'https://github.com/GUSTAVA009/hapych-music-studio',
      'git@github.com:GUSTAVA009/hapych-music-studio.git',
      'git@github.com:GUSTAVA009/hapych-music-studio')
    if ($LASTEXITCODE -ne 0 -or $origin -notin $allowed) {
      throw 'Not the official Git repository; refuse automatic update.'
    }
    $branch = (& git -C $target symbolic-ref --short HEAD).Trim()
    if ($LASTEXITCODE -ne 0 -or $branch -ne 'main') {
      throw 'Existing Git checkout is not on main. No changes were made.'
    }
    $edited = @(& git -C $target status --porcelain --untracked-files=no)
    if ($LASTEXITCODE -ne 0 -or $edited.Count -gt 0) {
      throw 'Existing Git code has local changes. Commit/back up your edits before enabling uninstaller.'
    }
    Write-Host 'Updating official Git checkout without reinstalling AI models...' -ForegroundColor Cyan
    & git -C $target pull --ff-only origin main
    if ($LASTEXITCODE -ne 0) { throw 'Safe fast-forward failed. Original app was preserved.' }
  }
  else {
    # ZIP installs have no Git metadata. Copy only the four uninstall/shortcut
    # support files. Never touch existing music, Python environments or app code.
    foreach ($f in $files) {
      $dst = Join-Path $target $f
      if (Test-Path -LiteralPath $dst) {
        if (-not (Test-Path -LiteralPath $dst -PathType Leaf)) {
          throw "Conflicting existing directory: $dst"
        }
        $oldHash = (Get-FileHash -LiteralPath $dst -Algorithm SHA256).Hash
        $newHash = (Get-FileHash -LiteralPath (Join-Path $source $f) -Algorithm SHA256).Hash
        if ($oldHash -ne $newHash) { throw "File is customized/older; refusing overwrite: $dst" }
      }
    }
    foreach ($f in $files) {
      $dst = Join-Path $target $f
      if (-not (Test-Path -LiteralPath $dst)) {
        New-Item -ItemType Directory -Path (Split-Path $dst -Parent) -Force | Out-Null
        Copy-Item -LiteralPath (Join-Path $source $f) -Destination $dst -ErrorAction Stop
      }
    }
  }
}
$registration = Join-Path $target 'scripts\Register-Windows.ps1'
if (-not (Test-Path -LiteralPath $registration -PathType Leaf)) {
  throw 'Missing Windows registration helper after preparing old installation.'
}
$argsList = @('-NoProfile','-ExecutionPolicy','Bypass','-File',$registration,'-Root',$target)
if ($TestMode) {
  $argsList += @('-TestMode','-ProgramsDir',$ProgramsDir,'-DesktopDir',$DesktopDir,'-RegistryPath',$RegistryPath)
}
& powershell.exe @argsList
if ($LASTEXITCODE -ne 0) { throw 'Failed to add Windows shortcuts and uninstall entry.' }
Write-Host '[PASS] Existing installation can be removed through Windows Installed apps.' -ForegroundColor Green
Write-Host 'No AI model was downloaded and no user tracks were deleted.'
