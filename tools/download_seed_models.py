#!/usr/bin/env python3
"""Download only public, original pretrained Seed-VC dependencies.

No voice dataset, user recordings, private profiles or trained owner checkpoint
is downloaded. Uses the SAME checkpoint cache folders as the real Seed-VC
inference scripts; all downloads are resumable via huggingface_hub.
"""
from __future__ import annotations
import argparse
import os
from pathlib import Path
import sys

def main() -> int:
    parser=argparse.ArgumentParser()
    parser.add_argument("--seed-root",type=Path,required=True)
    parser.add_argument("--core-only",action="store_true",help="Skip BigVGAN and Whisper model snapshots")
    args=parser.parse_args()
    root=args.seed_root.resolve()
    if not (root/"hf_utils.py").is_file():
        raise RuntimeError(f"Not a complete Seed-VC checkout: {root}")
    checkpoints=root/"checkpoints"
    checkpoints.mkdir(exist_ok=True,parents=True)
    os.environ["HF_HUB_DISABLE_XET"]="1"
    # Match inference_studio75.py's HF_HUB_CACHE setting.
    os.environ["HF_HUB_CACHE"]=str(checkpoints/"hf_cache")
    from huggingface_hub import hf_hub_download,snapshot_download
    entries=[
        ("Plachta/Seed-VC","DiT_seed_v2_uvit_whisper_base_f0_44k_bigvgan_pruned_ft_ema_v2.pth"),
        ("Plachta/Seed-VC","config_dit_mel_seed_uvit_whisper_base_f0_44k.yml"),
        ("lj1995/VoiceConversionWebUI","rmvpe.pt"),
        ("funasr/campplus","campplus_cn_common.bin"),
    ]
    for repo,filename in entries:
        print(f"[Seed-VC] {repo}/{filename}",flush=True)
        downloaded=Path(hf_hub_download(repo_id=repo,filename=filename,cache_dir=str(checkpoints)))
        if not downloaded.is_file() or downloaded.stat().st_size<100:
            raise RuntimeError(f"Incomplete model file: {repo}/{filename}")
        print(f"  -> {downloaded.stat().st_size//1024} KiB",flush=True)
    if not args.core_only:
        for repo in ("nvidia/bigvgan_v2_44khz_128band_512x","openai/whisper-base"):
            print(f"[Seed-VC] public model snapshot: {repo}",flush=True)
            output=Path(snapshot_download(repo_id=repo,cache_dir=os.environ["HF_HUB_CACHE"]))
            if not output.is_dir() or not any(output.iterdir()):
                raise RuntimeError(f"Missing model snapshot after download: {repo}")
    print("Seed-VC pretrained dependencies downloaded and verified.",flush=True)
    print("Personal voice reference WAVs and custom fine-tuned checkpoints are NOT bundled.",flush=True)
    return 0

if __name__=="__main__":
    try:sys.exit(main())
    except Exception as e:
        print(f"[Seed-VC] Model download failed: {e}",file=sys.stderr)
        sys.exit(1)
