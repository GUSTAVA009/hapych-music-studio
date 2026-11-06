#Requires -Version 5.1
# Disposable end-to-end verification of shortcuts, HKCU uninstall entry and data preservation.
# Never uses the user's real Music Studio directory or production registry key.
$ErrorActionPreference = 'Stop'
$source = Split-Path $PSScriptRoot -Parent
$register = Join-Path $source 'scripts\Register-Windows.ps1'
$uninstall = Join-Path $source 'scripts\Uninstall-Windows.ps1'
$testRoot = Join-Path $env:TEMP ('HAPYCH-Installer-Tests-' + [guid]::NewGuid().ToString('N'))
$fixture = Join-Path $testRoot 'Music Studio'
$links = Join-Path $testRoot 'Start Menu'
$desktop = Join-Path $testRoot 'Desktop'
$backups = Join-Path $testRoot 'Saved Data'
$reg = 'HKCU:\Software\HAPYCH-Installer-Tests\' + [guid]::NewGuid().ToString('N')
function New-Fixture {
  New-Item -ItemType Directory -Force -Path (Join-Path $fixture 'app'),(Join-Path $fixture 'scripts'),(Join-Path $fixture 'Voice Engine'),(Join-Path $fixture 'Мои треки'),(Join-Path $fixture 'Voice Profiles') | Out-Null
  [IO.File]::WriteAllText((Join-Path $fixture 'app\studio_server.py'),'print("sample")')
  [IO.File]::WriteAllText((Join-Path $fixture 'scripts\Start-MusicStudio.ps1'),'Write-Output "demo"')
  Copy-Item -LiteralPath $uninstall -Destination (Join-Path $fixture 'scripts\Uninstall-Windows.ps1')
  Copy-Item -LiteralPath (Join-Path $source 'Music Studio.ico') -Destination (Join-Path $fixture 'Music Studio.ico')
  [IO.File]::WriteAllText((Join-Path $fixture 'Мои треки\song.wav'),'private-song')
  [IO.File]::WriteAllText((Join-Path $fixture 'Voice Profiles\profile.json'),'private-profile')
  [IO.File]::WriteAllText((Join-Path $fixture 'Voice Engine\personal.wav'),'personal-recording')
  [IO.File]::WriteAllText((Join-Path $fixture 'unusual-personal-file.dat'),'personal-unknown')
}
function Register-Fixture {
  & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $register -Root $fixture -TestMode -ProgramsDir $links -DesktopDir $desktop -RegistryPath $reg
  if ($LASTEXITCODE -ne 0) { throw 'Registration failed' }
}
function Uninstall-Fixture([string]$mode) {
  & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $uninstall -Root $fixture -Mode $mode -TestMode -ProgramsDir $links -DesktopDir $desktop -RegistryPath $reg -BackupRoot $backups | Out-Host
  return [int]$LASTEXITCODE
}
try {
  New-Item -ItemType Directory -Force -Path $testRoot | Out-Null
  foreach ($script in @($register,$uninstall, (Join-Path $source 'scripts\Install-Windows.ps1'))) {
    $errors = $null; $tokens = $null
    [void][Management.Automation.Language.Parser]::ParseFile($script,[ref]$tokens,[ref]$errors)
    if (@($errors).Count -gt 0) { throw "Syntax errors in $script : $($errors[0])" }
  }
  New-Fixture
  Register-Fixture
  Register-Fixture
  if (-not (Test-Path (Join-Path $desktop 'HAPYCH Music Studio.lnk'))) { throw 'Missing Desktop icon' }
  if (-not (Test-Path (Join-Path $links 'Uninstall HAPYCH Music Studio.lnk'))) { throw 'Missing Start Menu uninstall link' }
  $entry = Get-ItemProperty -Path $reg
  if ($entry.DisplayName -ne 'HAPYCH Music Studio') { throw 'Windows Apps metadata wrong' }
  if ($entry.UninstallString -notmatch 'Uninstall-Windows.ps1') { throw 'Invalid Windows uninstall command' }
  Write-Host '[PASS] Registration, icon, Start Menu and Windows Apps entry are idempotent.'
  # A corrupt marker MUST abort the destructive phase.
  $markerPath = Join-Path $fixture '.hapych-installed.json'
  $marker = Get-Content -LiteralPath $markerPath -Raw -Encoding UTF8 | ConvertFrom-Json
  $marker.installRoot = 'C:\This-Is-Not-The-Installed-Program'
  $marker | ConvertTo-Json | Set-Content -LiteralPath $markerPath -Encoding UTF8
  if ((Uninstall-Fixture 'DeleteAll') -eq 0) { throw 'Wrong marker allowed deletion' }
  if (-not (Test-Path (Join-Path $fixture 'Мои треки\song.wav'))) { throw 'Wrong marker deleted user song' }
  Write-Host '[PASS] Unexpected root marker prevents deletion.'
  Register-Fixture
  if ((Uninstall-Fixture 'KeepData') -ne 0) { throw 'KeepData uninstall failed' }
  if (Test-Path -LiteralPath $fixture) { throw 'Application directory remains after uninstall' }
  if (Test-Path -LiteralPath $reg) { throw 'Registry entry remains after uninstall' }
  if (Test-Path (Join-Path $desktop 'HAPYCH Music Studio.lnk')) { throw 'Desktop shortcut remains' }
  $saved = @(Get-ChildItem -LiteralPath $backups -Directory)
  if ($saved.Count -ne 1) { throw 'Expected one saved data directory' }
  foreach ($entry in @('Мои треки\song.wav','Voice Profiles\profile.json','Voice Engine\personal.wav','unusual-personal-file.dat')) {
    if (-not (Test-Path (Join-Path $saved[0].FullName $entry))) { throw "Personal data was not preserved: $entry" }
  }
  Write-Host '[PASS] KeepData uninstalls the application but preserves recordings, profiles and unknown files.'
  New-Fixture
  Register-Fixture
  if ((Uninstall-Fixture 'DeleteAll') -ne 0) { throw 'DeleteAll uninstall failed' }
  if (Test-Path -LiteralPath $fixture) { throw 'DeleteAll did not remove application directory' }
  Write-Host '[PASS] Explicit DeleteAll mode removes isolated test installation.'
  Write-Host 'HAPYCH_WINDOWS_UNINSTALL_REGRESSION=PASS'
}
finally {
  if (Test-Path -LiteralPath $reg) { Remove-Item -LiteralPath $reg -Recurse -Force -ErrorAction SilentlyContinue }
  if (Test-Path -LiteralPath $testRoot) { Remove-Item -LiteralPath $testRoot -Recurse -Force -ErrorAction SilentlyContinue }
}
