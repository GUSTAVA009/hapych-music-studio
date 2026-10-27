#Requires -Version 5.1
# Unit-test safe installer shutdown decisions on synthetic socket owners.
# No actual process is killed and no user Music Studio data is touched.
$ErrorActionPreference='Stop'
$root=Join-Path (Split-Path $PSScriptRoot -Parent) 'scripts\Close-Studio-For-Install.ps1'
$tok=$null;$errs=$null
$ast=[Management.Automation.Language.Parser]::ParseFile($root,[ref]$tok,[ref]$errs)
if(@($errs).Count){throw 'Close-Studio-For-Install.ps1 contains syntax errors'}
$required=@('Get-HapychPortOwners','Test-ExactHapychScriptArgument','Get-HapychIdentity','Get-HapychServices',
            'Assert-HapychIdle','Confirm-OrphanACE','Stop-HapychService')
foreach($name in $required){
  $def=@($ast.FindAll({param($node)
    $node -is [Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -eq $name
  },$true))
  if($def.Count -ne 1){throw "Missing function: $name"}
  . ([ScriptBlock]::Create($def[0].Extent.Text))
}

$StudioPort=17770
$EnginePort=17862
$testRoot=Join-Path $env:TEMP 'HAPYCH-Synthetic-Music-Studio'
$studioFile=Join-Path $testRoot 'app\studio_server.py'
$aceFile=Join-Path $testRoot 'ACE-Step-1.5\.venv\Scripts\acestep.exe'
$script:FakeSockets=@()
$script:FakeProcesses=@{}
$script:FakeJobStatus='idle'
$script:Stopped=@()
$NoPrompt=$true
$AllowOrphanClose=$false
$CheckOnly=$false

function Get-NetTCPConnection {
  [CmdletBinding()]
  param([int]$LocalPort,[string]$State)
  return @($script:FakeSockets|Where-Object {$_.LocalPort -eq $LocalPort -and $_.State -eq $State})
}
function Get-CimInstance {
  [CmdletBinding()]
  param([string]$ClassName,[string]$Filter)
  $identity=[regex]::Match($Filter,'ProcessId = (\d+)')
  if(-not $identity.Success){return $null}
  $id=[int]$identity.Groups[1].Value
  return $script:FakeProcesses[$id]
}
function Invoke-RestMethod {
  [CmdletBinding()]
  param([string]$Uri,[int]$TimeoutSec)
  return [pscustomobject]@{
    name='Music Studio'
    job=[pscustomobject]@{status=$script:FakeJobStatus}
  }
}
function Stop-Process {
  [CmdletBinding()]
  param([int]$Id,[switch]$Force)
  $script:Stopped+= $Id
}
function Fake-Socket([int]$Port,[int]$Owner,[string]$Address='127.0.0.1'){
  return [pscustomobject]@{LocalPort=$Port;OwningProcess=$Owner;LocalAddress=$Address;State='Listen'}
}
$script:FakeSockets=@((Fake-Socket $StudioPort 51001),(Fake-Socket $EnginePort 51002))
$script:FakeProcesses[51001]=[pscustomobject]@{
  ExecutablePath='C:\Python\pythonw.exe'
  CommandLine=('"C:\Python\pythonw.exe" "'+$studioFile+'"')
}
$script:FakeProcesses[51002]=[pscustomobject]@{
  ExecutablePath='C:\Python\python.exe'
  CommandLine=('"C:\Python\python.exe" "'+$aceFile+'" --port '+$EnginePort)
}

# Correct command lines and listener PIDs are detected.
$running=@(Get-HapychServices)
if($running.Count -ne 2){throw ('Expected 2 owned listeners, got '+$running.Count)}
if(-not (Assert-HapychIdle -Services $running)){throw 'Idle Music Studio should be stoppable'}
foreach($item in $running){Stop-HapychService -Service $item}
if(@($script:Stopped|Sort-Object).Count -ne 2){throw 'Incorrect controlled stop count'}
if(@($script:Stopped|Where-Object {$_ -notin @(51001,51002)}).Count){throw 'Unexpected PID stopped'}
Write-Host 'PASS: Verified idle Music Studio + ACE-Step, only owned listener PIDs are eligible'
# uv-managed Python on GitHub-hosted Windows runners uses python3.exe.
$normal=$script:FakeProcesses[51002]
$script:FakeProcesses[51002]=[pscustomobject]@{
  ExecutablePath='C:\Python\python3.exe'
  CommandLine=('"C:\Python\python3.exe" "'+$aceFile+'" --port '+$EnginePort)
}
if(@(Get-HapychServices).Count -ne 2){throw 'uv-managed python3.exe listener not recognized'}
$script:FakeProcesses[51002]=$normal
Write-Host 'PASS: uv-managed python3.exe executable is recognized by exact script path'

# Same filename and identical contents at a DIFFERENT location must never
# pass the file-system alias check or allow termination.
$aliasFixture=Join-Path $env:TEMP ('HAPYCH-PathIdentity-QA-'+[Guid]::NewGuid().ToString('N'))
try{
  $first=Join-Path $aliasFixture 'owned\app\studio_server.py'
  $second=Join-Path $aliasFixture 'foreign\app\studio_server.py'
  New-Item -ItemType Directory -Force (Split-Path $first -Parent),(Split-Path $second -Parent)|Out-Null
  [IO.File]::WriteAllText($first,'EXACT SAME CONTENT',[Text.Encoding]::ASCII)
  [IO.File]::WriteAllText($second,'EXACT SAME CONTENT',[Text.Encoding]::ASCII)
  if(Test-ExactHapychScriptArgument -CommandLine ('"C:\Python\python3.exe" "'+$second+'"') -Expected $first){
    throw 'An unrelated copy with identical contents was incorrectly recognized'
  }
  if(-not(Test-ExactHapychScriptArgument -CommandLine ('"C:\Python\python3.exe" "'+$first+'"') -Expected $first)){
    throw 'The original installed script was not recognized'
  }
}finally{
  if(Test-Path $aliasFixture){Remove-Item -LiteralPath $aliasFixture -Recurse -Force -ErrorAction SilentlyContinue}
}
Write-Host 'PASS: Canonical file identity distinguishes identical copies at different paths'

# In-progress generation must never be interrupted.
$script:Stopped=@()
$script:FakeJobStatus='generating'
try{
  $null=Assert-HapychIdle -Services @(Get-HapychServices)
  throw 'Active generation was incorrectly accepted'
}catch{
  if($_.Exception.Message -notmatch 'active or unknown generation'){throw}
}
if($script:Stopped.Count){throw 'Active generation was interrupted'}
Write-Host 'PASS: Active generation prevents automatic shutdown'

# Unknown process on 7862 is not the user's Music Studio.
$script:FakeJobStatus='idle'
$original=$script:FakeProcesses[51002]
$script:FakeProcesses[51002]=[pscustomobject]@{
  ExecutablePath='C:\Python\python.exe'
  CommandLine='"C:\Python\python.exe" "C:\OtherMusic\third-party-engine.py"'
}
try{
  $null=Get-HapychServices
  throw 'Foreign process was incorrectly accepted'
}catch{
  if($_.Exception.Message -notmatch 'not a verified HAPYCH'){throw}
}
if($script:Stopped.Count){throw 'Foreign process was touched'}
$script:FakeProcesses[51002]=$original
Write-Host 'PASS: Foreign application owning 7862 is never stopped'

# Executable type must also be python.exe/pythonw.exe or acestep.exe.
$script:FakeProcesses[51002]=[pscustomobject]@{
  ExecutablePath='C:\Windows\explorer.exe'
  CommandLine='"C:\Windows\explorer.exe" "'+$aceFile+'"'
}
try{
  $null=Get-HapychServices
  throw 'Foreign executable with spoofed command line was incorrectly accepted'
}catch{
  if($_.Exception.Message -notmatch 'not a verified HAPYCH'){throw}
}
$script:FakeProcesses[51002]=$original
Write-Host 'PASS: Foreign executable identity rejected'

# If the server is gone and only ACE-Step remains, ask first.
$script:FakeSockets=@((Fake-Socket $EnginePort 51002))
$NoPrompt=$true
$AllowOrphanClose=$false
try{
  $null=Confirm-OrphanACE
  throw 'Orphan engine should require explicit confirmation'
}catch{
  if($_.Exception.Message -notmatch 'Without Music Studio'){throw}
}
$AllowOrphanClose=$true
if(-not (Confirm-OrphanACE)){throw 'Explicit orphan-engine approval rejected'}
Write-Host 'PASS: Orphan ACE-Step is protected against unattended termination'

# Make sure test was fully simulated; no real Windows PID was touched.
if(@($script:Stopped |Where-Object {$_ -lt 51000 -or $_ -gt 51002}).Count){throw 'Unexpected stopped PID in tests'}
Write-Host 'SAFE_STUDIO_SHUTDOWN_REGRESSION=PASS'
