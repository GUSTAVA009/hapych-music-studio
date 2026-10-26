#Requires -Version 5.1
# Regression for GitHub ZIP Install.cmd when %USERPROFILE%\Music Studio exists.
# Tests fast-forward update, personal data preservation, and refusal of unsafe targets.
# All testing is performed in a uniquely named temporary folder, never the real Music Studio.
$ErrorActionPreference='Stop'
$sourceBootstrap=Join-Path (Split-Path $PSScriptRoot -Parent) 'scripts\Bootstrap-Windows.ps1'
$testRoot=Join-Path $env:TEMP ('hapych-bootstrap-existing-'+[Guid]::NewGuid().ToString('N'))
$dest=Join-Path $testRoot 'Music Studio'
$nonGit=Join-Path $testRoot 'not-a-repository'
$url='https://github.com/GUSTAVA009/hapych-music-studio.git'
function Invoke-TestSync([string]$folder) {
  # Capture subprocess output: successful Git fetch/pull writes progress to stderr,
  # and PowerShell 5.1 incorrectly promotes redirected native stderr to errors.
  $prefix=Join-Path $testRoot ('bootstrap-'+[Guid]::NewGuid().ToString('N'))
  $stdout=$prefix+'.out.txt';$stderr=$prefix+'.err.txt'
  $q=[char]34
  $argsList='-NoProfile -ExecutionPolicy Bypass -File '+$q+$sourceBootstrap+$q
  $argsList+=' -SyncOnly -NoPrerequisites -TargetRoot '+$q+$folder+$q
  $process=Start-Process -FilePath 'powershell.exe' -ArgumentList $argsList -Wait -PassThru -NoNewWindow -RedirectStandardOutput $stdout -RedirectStandardError $stderr
  return [int]$process.ExitCode
}
try{
  New-Item -Path $testRoot -ItemType Directory -Force|Out-Null
  & git -c credential.helper= clone -q --depth 3 $url $dest
  if($LASTEXITCODE -ne 0){throw 'Unable to clone public test repository'}
  $remoteHead=(& git -C $dest rev-parse HEAD).Trim()
  $previous=(& git -C $dest rev-parse 'HEAD~1').Trim()
  if($previous -eq $remoteHead){throw 'Git test requires two published commits'}
  # Reset is permitted ONLY inside this disposable newly cloned test repo.
  & git -C $dest reset -q --hard $previous
  if($LASTEXITCODE -ne 0){throw 'Unable to create outdated fixture'}
  $userData=Join-Path $dest 'Мои треки'
  New-Item -Path $userData -ItemType Directory -Force|Out-Null
  $marker=Join-Path $userData 'local-song-stays-here.txt'
  [IO.File]::WriteAllText($marker,'preserve-my-track-123',[Text.Encoding]::UTF8)
  $rc=Invoke-TestSync $dest
  if($rc -ne 0){throw 'ZIP bootstrap did not safely update an existing old Git checkout'}
  $updated=(& git -C $dest rev-parse HEAD).Trim()
  if($updated -ne $remoteHead){throw "Wrong updated commit: $updated != $remoteHead"}
  if([IO.File]::ReadAllText($marker,[Text.Encoding]::UTF8) -ne 'preserve-my-track-123'){
    throw 'Private local song marker was modified/deleted'
  }
  Write-Host 'PASS: Old official Git installation fast-forwarded; personal track preserved.'
  # A second execution must be safe and idempotent.
  $rc=Invoke-TestSync $dest
  if($rc -ne 0){throw 'Second Git installation update was not idempotent'}
  Write-Host 'PASS: Repeated installation update is safe.'
  # Local tracked modifications must be rejected without any destructive reset.
  $readme=Join-Path $dest 'README.md'
  [IO.File]::AppendAllText($readme,[Environment]::NewLine+'PERSONAL_EDIT_MUST_SURVIVE')
  $readmeHash=(Get-FileHash $readme -Algorithm SHA256).Hash
  $rc=Invoke-TestSync $dest
  if($rc -eq 0){throw 'Unsafe update was incorrectly permitted on an edited tracked file'}
  if((Get-FileHash $readme -Algorithm SHA256).Hash -ne $readmeHash){throw 'Tracked edit was overwritten despite protection'}
  if(-not(Test-Path $marker)){throw 'Private marker was removed while refusing unsafe update'}
  Write-Host 'PASS: Git checkout with local code modifications is safely refused.'
  # A non-Git pre-existing installation should never be deleted or silently overwritten.
  New-Item -Path $nonGit -ItemType Directory -Force|Out-Null
  $foreignFile=Join-Path $nonGit 'personal-library.txt'
  [IO.File]::WriteAllText($foreignFile,'do-not-overwrite',[Text.Encoding]::UTF8)
  $rc=Invoke-TestSync $nonGit
  if($rc -eq 0){throw 'Non-Git installation was unexpectedly modified'}
  if([IO.File]::ReadAllText($foreignFile,[Text.Encoding]::UTF8) -ne 'do-not-overwrite'){
    throw 'Existing non-Git user file was overwritten'
  }
  Write-Host 'PASS: Existing non-Git user data is not touched.'
  Write-Host 'BOOTSTRAP_EXISTING_GIT_REGRESSION=PASS'
}finally{
  if(Test-Path $testRoot){Remove-Item -LiteralPath $testRoot -Force -Recurse -ErrorAction SilentlyContinue}
}
