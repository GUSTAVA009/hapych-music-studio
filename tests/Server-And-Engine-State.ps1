#Requires -Version 5.1
# Regression: the web server MUST be considered reachable when ACE-Step is
# still initializing. Previous Start-MusicStudio.ps1 incorrectly used
# health.ready (AI backend ready) and spawned a duplicate web server.
$ErrorActionPreference='Stop'
$path=Join-Path (Split-Path $PSScriptRoot -Parent) 'scripts\Start-MusicStudio.ps1'
$tokens=$null;$errors=$null
$ast=[System.Management.Automation.Language.Parser]::ParseFile($path,[ref]$tokens,[ref]$errors)
if(@($errors).Count){throw 'Start-MusicStudio.ps1 has parse errors'}
$matches=@($ast.FindAll({param($n)
  $n -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -eq 'Is-ServerAlive'
},$true))
if($matches.Count -ne 1){throw 'Is-ServerAlive function was not found'}
. ([ScriptBlock]::Create($matches[0].Extent.Text))
$url='http://127.0.0.1:7870'
function Invoke-RestMethod {return [pscustomobject]@{name='Music Studio';server_ready=$true;ready=$false}}
if(-not(Is-ServerAlive)){throw 'Web server incorrectly considered down during AI initialization'}
function Invoke-RestMethod {return [pscustomobject]@{name='Music Studio';server_ready=$false;ready=$false}}
if(-not(Is-ServerAlive)){throw 'Legacy healthy Music Studio was incorrectly considered down'}
function Invoke-RestMethod {throw 'Connection refused'}
if(Is-ServerAlive){throw 'Web server falsely claimed alive when socket connection was refused'}
Write-Host 'PASS: web server readiness remains independent from ACE-Step model initialization'
