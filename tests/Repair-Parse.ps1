$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot -Parent
$path=Join-Path $root 'scripts\Repair-Windows.ps1'
$tokens=$null
$errors=$null
[void][System.Management.Automation.Language.Parser]::ParseFile($path,[ref]$tokens,[ref]$errors)
if(@($errors).Count){foreach($issue in $errors){Write-Error $issue};exit 1}
Write-Output 'PASS: Repair-Windows.ps1 syntax'
