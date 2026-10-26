#Requires -Version 5.1
<#
Windows installation from the public HAPYCH Music Studio source repository.
Clone to %USERPROFILE%\Music Studio before running.
Does NOT export/import voice recordings, track libraries, secrets or weights.
#>
[CmdletBinding()]
param([switch]$Full,[switch]$DownloadModels,[switch]$ValidateOnly)
$ErrorActionPreference='Stop'
$repo=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$expected=[IO.Path]::GetFullPath((Join-Path $HOME 'Music Studio'))
if($PSVersionTable.PSVersion.Major -ge 6 -and -not $IsWindows){
  throw 'Windows 10/11 required'
}
function Require-Command([string]$name,[string]$help){
  if(-not(Get-Command $name -ErrorAction SilentlyContinue)){throw "$name not found. $help"}
}
if([IntPtr]::Size -ne 8){throw '64-bit Windows is required for the AI models.'}
if(-not(Test-Path (Join-Path $repo 'app\ui\index.html'))){throw 'UI source missing. Download a complete Music Studio archive.'}
$versionFile=Join-Path $repo 'third_party_versions.json'
if(-not(Test-Path $versionFile)){throw 'Missing third_party_versions.json (incomplete archive or clone).'}
$versions=Get-Content (Join-Path $repo 'third_party_versions.json') -Raw -Encoding UTF8|ConvertFrom-Json
function Invoke-Step([string]$label,[scriptblock]$command){
  Write-Host "[$label]" -ForegroundColor Cyan
  & $command
  if($LASTEXITCODE -ne 0){throw "Failed: $label (exit $LASTEXITCODE)"}
}
function Install-Pinned([string]$key,[string]$folder){
  $entry=$versions.$key
  $origin=[string]$entry.repo
  $sha=[string]$entry.commit
  if($sha -notmatch '^[0-9a-f]{40}$'){throw "Invalid pinned commit for $key"}
  # A clone must populate the working tree. Older installers used
  # 'git clone --no-checkout' and considered HEAD sufficient even when the
  # actual pyproject.toml / README.md files were missing.
  $requiredFile = switch ($key) {
    'ace-step' { 'pyproject.toml' }
    'apexsvc'  { 'pyproject.toml' }
    'seed-vc'  { 'README.md' }
    default    { 'README.md' }
  }
  $fresh=$false
  if(-not(Test-Path (Join-Path $folder '.git'))){
    if(Test-Path $folder){throw "Directory exists without Git metadata: $folder"}
    Invoke-Step "Clone $key (with working files)" { & git clone --depth 1 $origin $folder }
    $fresh=$true
  }
  $remote=(& git -C $folder remote get-url origin).Trim()
  if($remote -ine $origin){throw "Wrong upstream for $key : $remote"}
  $head=(& git -C $folder rev-parse HEAD).Trim()
  $requiredPath=Join-Path $folder $requiredFile
  if($head -eq $sha -and (Test-Path $requiredPath)){
    Write-Host "[$key] Checked out at pinned commit $sha" -ForegroundColor Green
    return
  }
  # Repair an old --no-checkout clone only if its worktree is really empty.
  # Never reset a folder containing files or local user modifications.
  $worktreeEntries=@(Get-ChildItem -LiteralPath $folder -Force |
      Where-Object { $_.Name -ne '.git' })
  $emptyWorktree=($worktreeEntries.Count -eq 0)
  if($head -eq $sha -and $emptyWorktree){
    Invoke-Step "Materialize missing $key files" { & git -C $folder reset --hard $sha }
  }else{
    if(-not $fresh){
      $modified=@(& git -C $folder status --porcelain=v1 -uno)
      if($modified.Count -gt 0 -and -not $emptyWorktree){
        throw "$key contains local changes; refusing checkout to protect your files"
      }
    }
    Invoke-Step "Fetch pinned $key commit" { & git -C $folder fetch --depth 1 origin $sha }
    Invoke-Step "Checkout pinned $key commit" { & git -C $folder checkout --detach $sha }
  }
  if(-not (Test-Path $requiredPath)){
    throw "$key checkout is incomplete: missing $requiredFile in $folder. No dependencies installed."
  }
}
Write-Host 'HAPYCH Music Studio / Windows installation' -ForegroundColor Green
Write-Host "Project: $repo" -ForegroundColor Cyan
if($ValidateOnly){
  Write-Host '[OK] Source files and required commands are accessible.' -ForegroundColor Green
  Write-Host '[INFO] -ValidateOnly does not download models or modify any files.'
  exit 0
}
Require-Command 'git' 'https://git-scm.com/download/win'
Require-Command 'uv' 'https://docs.astral.sh/uv/getting-started/installation/'
Require-Command 'ffmpeg' 'https://ffmpeg.org/download.html'
if($repo.TrimEnd('\') -ine $expected.TrimEnd('\')){
  throw "Clone to '$expected'. Some Music Studio modules expect that directory; actual: $repo"
}
# Never mutate Python environments while the local music server or ACE-Step
# are running. This can crash a user's in-progress generation or corrupt DLLs.
foreach($port in @(7870,7862)){
  $socket=New-Object System.Net.Sockets.TcpClient
  try{
    $connect=$socket.BeginConnect('127.0.0.1',$port,$null,$null)
    if($connect.AsyncWaitHandle.WaitOne(350)){
      try{$socket.EndConnect($connect)}catch{}
      if($socket.Connected){
        throw "Music Studio / ACE-Step is still running on port $port. Close Music Studio and its ACE-Step processes before updating; then rerun Install.cmd. No user data has been modified."
      }
    }
  }finally{$socket.Close()}
}
$env:PYTHONUTF8='1'
$env:HF_HUB_DISABLE_XET='1'
Invoke-Step 'Python 3.11 for ACE-Step' { & uv python install 3.11 }
$ace=Join-Path $repo 'ACE-Step-1.5'
Install-Pinned 'ace-step' $ace
Push-Location $ace
try{Invoke-Step 'ACE-Step v1.5 dependencies (preserve Studio extras)' { & uv sync --project $ace --frozen --inexact --python 3.11 }}
finally{Pop-Location}
$acePython=Join-Path $ace '.venv\Scripts\python.exe'
if(-not(Test-Path $acePython)){throw 'ACE-Step Python executable not found'}
if(-not(Test-Path (Join-Path $ace '.venv\Scripts\acestep.exe'))){throw 'ACE-Step installation incomplete: missing acestep.exe'}
if($DownloadModels){
  $downloader=Join-Path $ace '.venv\Scripts\acestep-download.exe'
  if(-not(Test-Path $downloader)){throw 'ACE-Step downloader missing.'}
  Push-Location $ace
  try{Invoke-Step 'Download official ACE-Step main and LLM models' { & $downloader }}
  finally{Pop-Location}
}
Invoke-Step 'Music Studio app extras' {
  & uv pip install --python $acePython -r (Join-Path $repo 'requirements\studio-extra.txt')
}
foreach($dir in @('Мой голос','Мои треки','Исходные версии','Мастер WAV',
                   'Voice Profiles','Integrations','Exports','Sound Library')){
  New-Item -ItemType Directory -Force -Path (Join-Path $repo $dir)|Out-Null
}
if($Full){
  $seed=Join-Path $repo 'Voice Engine\seed-vc'
  $apex=Join-Path $repo 'Voice Engine\alternatives\ApexSVC'
  Install-Pinned 'seed-vc' $seed
  Install-Pinned 'apexsvc' $apex
  $overlay=Join-Path $repo 'overlays\seed-vc'
  $overlayInstaller=Join-Path $repo 'tools\install_seed_overlays.py'
  if(-not(Test-Path $overlayInstaller)){throw 'Seed-VC overlay installer missing.'}
  Invoke-Step 'Install/update HAPYCH Seed-VC modules with safe backups' {
    & $acePython -X utf8 $overlayInstaller --seed-root $seed --overlay $overlay --expected-commit $versions.'seed-vc'.commit
  }
  $patch=Join-Path $repo 'overlays\apexsvc_custom.patch'
  $patcher=Join-Path $repo 'tools\apply_apex_patch.py'
  if(-not(Test-Path $patcher)){throw 'Missing ApexSVC compatibility patch installer.'}
  # Git apply --reverse --check returns 1 for a clean, unpatched tree.
  # PowerShell 5.1 treated that expected Git stderr as a NativeCommandError.
  # The Python helper checks every file before modifying any target, then
  # applies missing sections and recovers from partial patch application.
  Invoke-Step 'Check and apply ApexSVC compatibility patch safely' {
    & $acePython -X utf8 $patcher --repo $apex --patch $patch --expected-commit $versions.apexsvc.commit
  }
  Invoke-Step 'Install Python 3.11' { & uv python install 3.11 }
  $voiceEnv=Join-Path $repo 'Voice Engine\.venv'
  $voicePython=Join-Path $voiceEnv 'Scripts\python.exe'
  if(-not(Test-Path $voicePython)){
    Invoke-Step 'Create voice-engine venv' { & uv venv --python 3.11 $voiceEnv }
  }
  $uvPipHelp = (& uv pip install --help | Out-String)
  if($uvPipHelp -notmatch '--torch-backend'){
    throw "uv is outdated: the --torch-backend option is required. Update it with 'winget upgrade --id astral-sh.uv -e', then rerun setup."
  }
  # Use PyPI for normal packages, e.g. certifi, and the official PyTorch
  # CUDA 12.1 index ONLY for torch, torchvision and torchaudio.
  # uv's --extra-index-url takes precedence and can select a stale certifi
  # before checking PyPI. Keep dependency-confusion protection enabled.
  Invoke-Step 'Install pinned voice-engine packages (PyPI + PyTorch CUDA 12.1)' {
    & uv pip install --python $voicePython --default-index 'https://pypi.org/simple' --torch-backend cu121 -r (Join-Path $repo 'requirements\voice-engine-win-lock.txt')
  }
  # Resemblyzer 0.1.4 declares webrtcvad>=2.0.10, but PyPI distributes
  # webrtcvad as source-only on Windows. Its native C extension fails to
  # build on machines without Visual Studio C++ Build Tools. We explicitly
  # installed webrtcvad-wheels above (provides import webrtcvad). Avoid
  # pulling the obsolete source package and typing backport on Python 3.11.
  Invoke-Step 'Install Resemblyzer without obsolete source dependencies' {
    & uv pip install --python $voicePython --default-index 'https://pypi.org/simple' --no-deps --only-binary :all: 'resemblyzer==0.1.4'
  }
  Invoke-Step 'Verify voice dependencies + native audio libraries' {
    & $voicePython -X utf8 (Join-Path $repo 'tools\verify_voice_runtime.py')
  }
  Invoke-Step 'Install Python 3.10 for ApexSVC' { & uv python install 3.10 }
  Push-Location $apex
  try{Invoke-Step 'Install ApexSVC pinned environment' { & uv sync --project $apex --frozen --inexact --python 3.10 }}
  finally{Pop-Location}
  if($DownloadModels){
    Push-Location $apex
    try{
      $apexPython=Join-Path $apex '.venv\Scripts\python.exe'
      if(-not(Test-Path $apexPython)){throw 'ApexSVC venv missing'}
      Invoke-Step 'Download ApexSVC model weights' { & $apexPython scripts/download_models.py }
      foreach($name in @('G_150k.pt','WavLM-Large.pt')){
        $model=Join-Path $apex ('checkpoints\'+$name)
        if(-not(Test-Path $model) -or (Get-Item $model).Length -lt 20000000){throw "ApexSVC model is missing or incomplete: $name"}
      }
    }
    finally{Pop-Location}
    $voicePy=Join-Path $repo 'Voice Engine\.venv\Scripts\python.exe'
    $seedDownloader=Join-Path $repo 'tools\download_seed_models.py'
    if(Test-Path $seedDownloader){
      Push-Location $seed
      try{Invoke-Step 'Download Seed-VC public pretrained models' { & $voicePy -X utf8 $seedDownloader --seed-root $seed }}
      finally{Pop-Location}
    }
  }
}
Write-Host ''
Write-Host 'Source and selected Python dependencies are installed.' -ForegroundColor Green
Write-Host 'On first run ACE-Step may download large pretrained models.' -ForegroundColor Yellow
Write-Host 'Seed-VC and OpenUtau models are separate and subject to their own licenses.' -ForegroundColor Yellow
Write-Host 'Run .\scripts\Verify-Install.ps1, then .\scripts\Start-MusicStudio.ps1'
