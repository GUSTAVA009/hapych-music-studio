#Requires -Version 5.1
# Regression for owners of pre-shortcut ZIP installs; all files live in TEMP.
$ErrorActionPreference = 'Stop'
$source = Split-Path $PSScriptRoot -Parent
$enable = Join-Path $source 'scripts\Enable-Uninstall-Existing.ps1'
$uninstall = Join-Path $source 'scripts\Uninstall-Windows.ps1'
$test = Join-Path $env:TEMP ('hapych-existing-uninstall-' + [Guid]::NewGuid().ToString('N'))
$existing = Join-Path $test 'Music Studio'
$bad = Join-Path $test 'Not-Music'
$conflict = Join-Path $test 'Conflict'
$start = Join-Path $test 'Start Menu'
$desktop = Join-Path $test 'Desktop'
$backups = Join-Path $test 'Backups'
$registry = 'HKCU:\Software\HAPYCH-Installer-Tests\' + [Guid]::NewGuid().ToString('N')
function New-OldFixture([string]$folder) {
  foreach ($f in @('app','scripts','My Music','ACE-Step-1.5\checkpoints')) {
    New-Item -ItemType Directory -Force -Path (Join-Path $folder $f) | Out-Null
  }
  [IO.File]::WriteAllText((Join-Path $folder 'app\studio_server.py'),'print("fixture")')
  [IO.File]::WriteAllText((Join-Path $folder 'scripts\Start-MusicStudio.ps1'),'Write-Output "fixture"')
  [IO.File]::WriteAllText((Join-Path $folder 'third_party_versions.json'),'{}')
  [IO.File]::WriteAllText((Join-Path $folder 'My Music\track.wav'),'private song')
  [IO.File]::WriteAllText((Join-Path $folder 'ACE-Step-1.5\checkpoints\model.safetensors'),'model remains')
}
function Invoke-Enable([string]$folder,[string]$reg) {
  $out = Join-Path $test ([Guid]::NewGuid().ToString('N') + '.out')
  $err = $out + '.err'
  $argsList = '-NoProfile -ExecutionPolicy Bypass -File "' + $enable +
    '" -TargetRoot "' + $folder + '" -TestMode -ProgramsDir "' + $start +
    '" -DesktopDir "' + $desktop + '" -RegistryPath "' + $reg + '"'
  $p = Start-Process -FilePath 'powershell.exe' -ArgumentList $argsList -NoNewWindow -Wait -PassThru -RedirectStandardOutput $out -RedirectStandardError $err
  if ($p.ExitCode -ne 0) { Write-Host ('Expected/actual failure: ' + ((Get-Content $err -Raw -ErrorAction SilentlyContinue) | Select-Object -First 1).Trim().Substring(0,50)) }
  return [int]$p.ExitCode
}
try {
  New-Item -ItemType Directory -Force -Path $test | Out-Null
  New-OldFixture $existing
  $song = Join-Path $existing 'My Music\track.wav'
  $model = Join-Path $existing 'ACE-Step-1.5\checkpoints\model.safetensors'
  $songHash = (Get-FileHash $song -Algorithm SHA256).Hash
  $modelHash = (Get-FileHash $model -Algorithm SHA256).Hash
  if ((Invoke-Enable $existing $registry) -ne 0) { throw 'Upgrade old ZIP installation failed.' }
  if ((Invoke-Enable $existing $registry) -ne 0) { throw 'Upgrade is not repeatable.' }
  foreach ($f in @('Uninstall.cmd','scripts\Uninstall-Windows.ps1','scripts\Register-Windows.ps1','Music Studio.ico','.hapych-installed.json')) {
    if (-not (Test-Path -LiteralPath (Join-Path $existing $f))) { throw "Missing migrated file: $f" }
  }
  if (-not (Test-Path -LiteralPath (Join-Path $desktop 'HAPYCH Music Studio.lnk'))) { throw 'Desktop shortcut missing.' }
  if (-not (Test-Path -LiteralPath (Join-Path $start 'Uninstall HAPYCH Music Studio.lnk'))) { throw 'Start Menu uninstaller missing.' }
  $entry = Get-ItemProperty -Path $registry
  if ($entry.DisplayName -ne 'HAPYCH Music Studio' -or $entry.UninstallString -notmatch 'Uninstall-Windows.ps1') {
    throw 'Windows uninstaller registration invalid.'
  }
  if ((Get-FileHash $song -Algorithm SHA256).Hash -ne $songHash -or
      (Get-FileHash $model -Algorithm SHA256).Hash -ne $modelHash) {
    throw 'Personal files/models changed while enabling uninstall.'
  }
  Write-Host 'PASS: Existing ZIP install updated twice, user song/model unchanged, shortcuts and Apps registration present.'
  # A custom file must not be overwritten even when other supporting files are missing.
  New-OldFixture $conflict
  [IO.File]::WriteAllText((Join-Path $conflict 'scripts\Uninstall-Windows.ps1'),'custom important code')
  $conflictReg = $registry + '_conflict'
  if ((Invoke-Enable $conflict $conflictReg) -eq 0) { throw 'Custom file was overwritten.' }
  if ([IO.File]::ReadAllText((Join-Path $conflict 'scripts\Uninstall-Windows.ps1')) -ne 'custom important code') {
    throw 'Conflicting uninstaller was modified.'
  }
  if (Test-Path -LiteralPath (Join-Path $conflict '.hapych-installed.json')) { throw 'Conflict created a false install marker.' }
  Write-Host 'PASS: Customized files are protected, no false Windows registration.'
  New-Item -ItemType Directory -Force -Path $bad | Out-Null
  [IO.File]::WriteAllText((Join-Path $bad 'private.txt'),'secret stays')
  if ((Invoke-Enable $bad ($registry + '_bad')) -eq 0) { throw 'Unrelated folder accepted.' }
  if (-not (Test-Path -LiteralPath (Join-Path $bad 'private.txt'))) { throw 'Foreign folder was modified.' }
  Write-Host 'PASS: Unrelated directory rejected.'
  # Finally uninstall the upgraded old ZIP and verify the saved song survives.
  $argsList = '-NoProfile -ExecutionPolicy Bypass -File "' + $uninstall +
      '" -Root "' + $existing + '" -Mode KeepData -TestMode -ProgramsDir "' +
      $start + '" -DesktopDir "' + $desktop + '" -RegistryPath "' +
      $registry + '" -BackupRoot "' + $backups + '"'
  $p = Start-Process -FilePath 'powershell.exe' -ArgumentList $argsList -NoNewWindow -Wait -PassThru
  if ($p.ExitCode -ne 0 -or (Test-Path -LiteralPath $existing)) { throw 'Old installation uninstall failed.' }
  $saved = @(Get-ChildItem -LiteralPath $backups -Directory)
  if ($saved.Count -ne 1 -or -not (Test-Path -LiteralPath (Join-Path $saved[0].FullName 'My Music\track.wav'))) {
    throw 'Customer music was not saved during uninstall.'
  }
  Write-Host 'PASS: Previously installed ZIP can be uninstalled with private music safely retained.'
  Write-Host 'LEGACY_UNINSTALL_MIGRATION=PASS'
} finally {
  foreach ($item in @($registry,$registry+'_conflict',$registry+'_bad')) {
    if (Test-Path $item) { Remove-Item -Path $item -Recurse -Force -ErrorAction SilentlyContinue }
  }
  if (Test-Path -LiteralPath $test) { Remove-Item -LiteralPath $test -Recurse -Force -ErrorAction SilentlyContinue }
}
