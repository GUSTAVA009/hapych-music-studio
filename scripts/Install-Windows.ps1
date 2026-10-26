#Requires -Version 5.1
<#
Windows install from private source-only GitHub repository.
Clone to %USERPROFILE%\Music Studio before running.
Does NOT export/import voice recordings, track libraries, secrets or weights.
#>
[CmdletBinding()]
param([switch]$Full,[switch]$DownloadModels)
$ErrorActionPreference='Stop'
$repo=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$expected=[IO.Path]::GetFullPath((Join-Path $HOME 'Music Studio'))
if($repo.TrimEnd('\') -ine $expected.TrimEnd('\')){
  throw "Clone to '$expected'. Some Music Studio modules expect that directory; actual: $repo"
}
if($PSVersionTable.PSVersion.Major -ge 6 -and -not $IsWindows){
  throw 'Windows 10/11 required'
}
function Require-Command([string]$name,[string]$help){
  if(-not(Get-Command $name -ErrorAction SilentlyContinue)){throw "$name not found. $help"}
}
Require-Command 'git' 'https://git-scm.com/download/win'
Require-Command 'uv' 'https://docs.astral.sh/uv/getting-started/installation/'
Require-Command 'ffmpeg' 'https://ffmpeg.org/download.html'
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
$ace=Join-Path $repo 'ACE-Step-1.5'
Install-Pinned 'ace-step' $ace
Push-Location $ace
try{Invoke-Step 'ACE-Step v1.5 dependencies (large download)' { & uv sync --project $ace --frozen }}
finally{Pop-Location}
$acePython=Join-Path $ace '.venv\Scripts\python.exe'
if(-not(Test-Path $acePython)){throw 'ACE-Step Python executable not found'}
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
  Get-ChildItem $overlay -Recurse -File -Filter '*.py'|ForEach-Object{
    $relative=$_.FullName.Substring($overlay.Length).TrimStart('\')
    $target=Join-Path $seed $relative
    New-Item -ItemType Directory -Force -Path (Split-Path $target -Parent)|Out-Null
    if(Test-Path $target){
      $a=(Get-FileHash $_.FullName -Algorithm SHA256).Hash
      $b=(Get-FileHash $target -Algorithm SHA256).Hash
      if($a -ne $b){throw "Seed-VC patch conflicts with existing file: $relative"}
    }else{Copy-Item $_.FullName $target}
  }
  $patch=Join-Path $repo 'overlays\apexsvc_custom.patch'
  & git -C $apex apply --reverse --check $patch 2>$null
  if($LASTEXITCODE -ne 0){
    Invoke-Step 'Verify ApexSVC compatibility patch' { & git -C $apex apply --check $patch }
    Invoke-Step 'Apply ApexSVC compatibility patch' { & git -C $apex apply $patch }
  }else{Write-Host 'ApexSVC compatibility patch already applied.'}
  Invoke-Step 'Install Python 3.11' { & uv python install 3.11 }
  $voiceEnv=Join-Path $repo 'Voice Engine\.venv'
  $voicePython=Join-Path $voiceEnv 'Scripts\python.exe'
  if(-not(Test-Path $voicePython)){
    Invoke-Step 'Create voice-engine venv' { & uv venv --python 3.11 $voiceEnv }
  }
  Invoke-Step 'Install pinned voice-engine packages + CUDA 12.8' {
    & uv pip install --python $voicePython --extra-index-url 'https://download.pytorch.org/whl/cu128' -r (Join-Path $repo 'requirements\voice-engine-win-lock.txt')
  }
  Invoke-Step 'Install Python 3.10 for ApexSVC' { & uv python install 3.10 }
  Push-Location $apex
  try{Invoke-Step 'Install ApexSVC pinned environment' { & uv sync --project $apex --frozen --python 3.10 }}
  finally{Pop-Location}
  if($DownloadModels){
    Push-Location $apex
    try{Invoke-Step 'Download ApexSVC model weights' { & uv run --no-sync python scripts/download_models.py }}
    finally{Pop-Location}
  }
}
Write-Host ''
Write-Host 'Source and selected Python dependencies are installed.' -ForegroundColor Green
Write-Host 'On first run ACE-Step may download large pretrained models.' -ForegroundColor Yellow
Write-Host 'Seed-VC and OpenUtau models are separate and subject to their own licenses.' -ForegroundColor Yellow
Write-Host 'Run .\scripts\Verify-Install.ps1, then .\scripts\Start-MusicStudio.ps1'
