#Requires -Version 5.1
# Regression for a failed ACE-Step clone --no-checkout, Windows PowerShell 5.1.
$ErrorActionPreference='Stop'
$root=Join-Path $env:TEMP ('hapych-install-recovery-'+[Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Force $root|Out-Null
$origin=Join-Path $root 'origin'
$clone=Join-Path $root 'empty-checkout'
try {
  New-Item -ItemType Directory -Force $origin|Out-Null
  & git -C $origin init -q
  if($LASTEXITCODE -ne 0){throw 'git init failed'}
  & git -C $origin config user.email 'test@example.invalid'
  & git -C $origin config user.name 'Installer Regression'
  [IO.File]::WriteAllText((Join-Path $origin 'pyproject.toml'),'[project]'+"`n"+'name = "installer-probe"'+"`n"+'version = "0.0.1"'+"`n")
  & git -C $origin add pyproject.toml
  & git -C $origin commit -qm 'Mock upstream source'
  $sha=(& git -C $origin rev-parse HEAD).Trim()
  & git clone -q --no-checkout $origin $clone
  if($LASTEXITCODE -ne 0){throw 'git clone failed'}
  if(Test-Path (Join-Path $clone 'pyproject.toml')){throw 'Test precondition: clone was already materialized'}
  $versions=[pscustomobject]@{'ace-step'=[pscustomobject]@{repo=$origin;commit=$sha}}
  function Invoke-Step([string]$label,[scriptblock]$command){
    & $command
    if($LASTEXITCODE -ne 0){throw "$label failed $LASTEXITCODE"}
  }
  $installer=Join-Path (Split-Path $PSScriptRoot -Parent) 'scripts\Install-Windows.ps1'
  $tokens=$null;$parseErrors=$null
  $ast=[System.Management.Automation.Language.Parser]::ParseFile($installer,[ref]$tokens,[ref]$parseErrors)
  if(@($parseErrors).Count -ne 0){throw 'Installer has PowerShell syntax errors'}
  $method=@($ast.FindAll({param($node) $node -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -eq 'Install-Pinned'},$true))
  if($method.Count -ne 1){throw 'Install-Pinned function not found'}
  . ([ScriptBlock]::Create($method[0].Extent.Text))
  Install-Pinned 'ace-step' $clone
  if(-not (Test-Path (Join-Path $clone 'pyproject.toml'))){throw 'Recovery did not materialize pyproject'}
  if((& git -C $clone rev-parse HEAD).Trim() -ne $sha){throw 'Recovered repository at wrong commit'}
  Install-Pinned 'ace-step' $clone
  if(-not (Test-Path (Join-Path $clone 'pyproject.toml'))){throw 'Idempotent run erased files'}
  'PASS: empty --no-checkout clone recovered, pinned SHA preserved, second run safe'
}finally{
  if(Test-Path $root){Remove-Item -LiteralPath $root -Recurse -Force -ErrorAction SilentlyContinue}
}
