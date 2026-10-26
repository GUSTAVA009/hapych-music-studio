#Requires -Version 5.1
# Regression: installer updates PATH multiple times when probing git, uv, ffmpeg.
# PATH must NOT double/expand with each availability check.
$ErrorActionPreference='Stop'
$file=Join-Path (Split-Path $PSScriptRoot -Parent) 'scripts\Bootstrap-Windows.ps1'
$tokens=$null;$errors=$null
$ast=[Management.Automation.Language.Parser]::ParseFile($file,[ref]$tokens,[ref]$errors)
if(@($errors).Count){throw 'Bootstrap-Windows.ps1 does not parse'}
$method=@($ast.FindAll({param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -eq 'Refresh-Path'},$true))
if($method.Count -ne 1){throw 'Refresh-Path is missing'}
. ([ScriptBlock]::Create($method[0].Extent.Text))
Refresh-Path
$once=$env:Path
for($i=0;$i -lt 45;$i++){Refresh-Path}
$after=$env:Path
if($once -cne $after){throw 'Repeated Refresh-Path duplicated entries or altered path'}
if($after.Length -gt 27000){throw ('PATH is unexpectedly large: '+$after.Length)}
Write-Host ('PATH_REFRESH=PASS entries='+@($after -split ';').Count+' characters='+$after.Length)
