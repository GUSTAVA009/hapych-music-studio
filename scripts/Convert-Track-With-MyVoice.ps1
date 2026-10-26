#Requires -Version 5.1
<#
Convert a locally generated song to an authorized voice, preserving the
instrumental. This is experimental and does not register the track in UI.
Requires -Full ApexSVC install and working Demucs; produces NEW files only.
#>
[CmdletBinding()]
param(
 [Parameter(Mandatory=$true)][string]$Source,
 [Parameter(Mandatory=$true)][string[]]$References,
 [Parameter(Mandatory=$true)][string]$OutputWav,
 [ValidateSet('cpu','cuda')][string]$Device='cpu'
)
$ErrorActionPreference='Stop'
$root=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$sourceFile=(Resolve-Path -LiteralPath $Source -ErrorAction Stop).Path
$out=[IO.Path]::GetFullPath($OutputWav)
if([IO.Path]::GetExtension($out).ToLowerInvariant() -ne '.wav'){throw 'OutputWav must end with .wav'}
if(Test-Path $out){throw 'Output already exists, refusing overwrite'}
if($References.Count -lt 1 -or $References.Count -gt 3){throw 'Specify one to three voice reference recordings'}
$voiceFiles=@()
foreach($ref in $References){$voiceFiles+= (Resolve-Path -LiteralPath $ref -ErrorAction Stop).Path}
$ace=Join-Path $root 'ACE-Step-1.5\.venv\Scripts\python.exe'
$apex=Join-Path $root 'Voice Engine\alternatives\ApexSVC'
$apexPy=Join-Path $apex '.venv\Scripts\python.exe'
foreach($p in @($ace,$apexPy)){
 if(-not(Test-Path $p)){throw "Missing installed Python: $p. Run Install-Windows.ps1 -Full"}
}
$stemCache=Join-Path $root 'Integrations\DemucsScratch'
New-Item -ItemType Directory -Force $stemCache|Out-Null
$env:PYTHONUTF8='1'
Write-Host 'Separating vocal from original backing (may take considerable time)...' -ForegroundColor Cyan
& $ace -X utf8 -m demucs -n htdemucs --two-stems=vocals -d $Device -o $stemCache $sourceFile
if($LASTEXITCODE -ne 0){throw 'Demucs stem separation failed'}
$stem=Join-Path (Join-Path $stemCache 'htdemucs') ([IO.Path]::GetFileNameWithoutExtension($sourceFile))
$vocal=Join-Path $stem 'vocals.wav'
$instrumental=Join-Path $stem 'no_vocals.wav'
if(-not(Test-Path $vocal) -or -not(Test-Path $instrumental)){
 throw "Expected stems missing: $stem"
}
$argsList=@('-X','utf8',(Join-Path $root 'tools\convert_apex_stems.py'),
 '--vocals',$vocal,'--instrumental',$instrumental,'--output',$out,
 '--preset',(Join-Path $root 'presets\QA133_ConsonantProtection.json'),
 '--apex',$apex,'--device',$Device)
foreach($r in $voiceFiles){$argsList+=@('--reference',$r)}
Write-Host 'Converting the isolated vocal with ApexSVC; keeping instrumental untouched...' -ForegroundColor Cyan
& $apexPy @argsList
if($LASTEXITCODE -ne 0){throw 'ApexSVC conversion failed. Original song is unchanged.'}
Write-Host "New master: $out" -ForegroundColor Green
Write-Host "New MP3: $([IO.Path]::ChangeExtension($out,'.mp3'))" -ForegroundColor Green
