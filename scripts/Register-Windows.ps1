#Requires -Version 5.1
<#
Register HAPYCH Music Studio in the current user's Windows Apps list.
Creates Start Menu / Desktop shortcuts. No elevation required.
TestMode is for disposable test fixtures only.
#>
[CmdletBinding()]
param(
  [string]$Root = (Join-Path $HOME 'Music Studio'),
  [switch]$TestMode,
  [string]$ProgramsDir,
  [string]$DesktopDir,
  [string]$RegistryPath
)
$ErrorActionPreference = 'Stop'
if ([Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT) { throw 'Windows is required.' }
$rootPath = [IO.Path]::GetFullPath($Root).TrimEnd('\')
$expected = [IO.Path]::GetFullPath((Join-Path $HOME 'Music Studio')).TrimEnd('\')
if (-not $TestMode -and $rootPath -ine $expected) {
  throw "Refusing to register unexpected installation folder: $rootPath"
}
foreach ($file in @('app\studio_server.py','scripts\Start-MusicStudio.ps1','scripts\Uninstall-Windows.ps1','Music Studio.ico')) {
  if (-not (Test-Path -LiteralPath (Join-Path $rootPath $file) -PathType Leaf)) {
    throw "Incomplete installation: $file"
  }
}
if (-not $ProgramsDir) { $ProgramsDir = Join-Path ([Environment]::GetFolderPath('Programs')) 'HAPYCH Music Studio' }
if (-not $DesktopDir) { $DesktopDir = [Environment]::GetFolderPath('DesktopDirectory') }
if (-not $RegistryPath) { $RegistryPath = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\HAPYCHMusicStudio' }
if ($TestMode) {
  if (-not $ProgramsDir -or -not $DesktopDir -or $RegistryPath -notlike 'HKCU:\Software\HAPYCH-Installer-Tests\*') {
    throw 'TestMode requires isolated Start Menu, Desktop and HKCU test registry path.'
  }
}
$icon = Join-Path $rootPath 'Music Studio.ico'
$startScript = Join-Path $rootPath 'scripts\Start-MusicStudio.ps1'
$uninstallScript = Join-Path $rootPath 'scripts\Uninstall-Windows.ps1'
$powershell = Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
if (-not(Test-Path -LiteralPath $powershell)) { throw 'Windows PowerShell not found.' }
$marker = Join-Path $rootPath '.hapych-installed.json'
# Write this marker only after the source and uninstaller were verified.
$markerData = @{ product = 'HAPYCH Music Studio'; installRoot = $rootPath; schema = 1 } | ConvertTo-Json
[IO.File]::WriteAllText($marker, $markerData, (New-Object System.Text.UTF8Encoding($false)))
New-Item -ItemType Directory -Force -Path $ProgramsDir, $DesktopDir | Out-Null
$shell = New-Object -ComObject WScript.Shell
function New-MusicShortcut([string]$file, [string]$script, [string]$description) {
  $shortcut = $shell.CreateShortcut($file)
  $shortcut.TargetPath = $powershell
  $shortcut.Arguments = '-NoProfile -ExecutionPolicy Bypass -File "' + $script + '"'
  $shortcut.WorkingDirectory = $rootPath
  $shortcut.IconLocation = $icon + ',0'
  $shortcut.Description = $description
  $shortcut.Save()
}
New-MusicShortcut (Join-Path $ProgramsDir 'HAPYCH Music Studio.lnk') $startScript 'Open the local HAPYCH Music Studio'
New-MusicShortcut (Join-Path $ProgramsDir 'Uninstall HAPYCH Music Studio.lnk') $uninstallScript 'Remove the studio and optionally retain personal data'
New-MusicShortcut (Join-Path $DesktopDir 'HAPYCH Music Studio.lnk') $startScript 'Open the local HAPYCH Music Studio'
New-Item -Path $RegistryPath -Force | Out-Null
$values = @{
  DisplayName = 'HAPYCH Music Studio'
  DisplayVersion = '0.2.8-beta'
  Publisher = 'HAPYCH Music Studio'
  DisplayIcon = $icon
  InstallLocation = $rootPath
  UninstallString = '"' + $powershell + '" -NoProfile -ExecutionPolicy Bypass -File "' + $uninstallScript + '"'
}
foreach ($key in $values.Keys) { New-ItemProperty -Path $RegistryPath -Name $key -Value $values[$key] -PropertyType String -Force | Out-Null }
New-ItemProperty -Path $RegistryPath -Name NoModify -Value 1 -PropertyType DWord -Force | Out-Null
New-ItemProperty -Path $RegistryPath -Name NoRepair -Value 1 -PropertyType DWord -Force | Out-Null
Write-Host '[PASS] HAPYCH Music Studio is listed in Windows Installed apps.' -ForegroundColor Green
Write-Host 'Start Menu shortcut, Desktop icon and Uninstall action created.' -ForegroundColor Green
