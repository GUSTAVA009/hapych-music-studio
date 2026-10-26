#!/usr/bin/env python3
"""Read-only verifier: app source, Python envs, vendored overlays, checkpoints.

Outputs structured JSON. This checks installation integrity, *not* singer
quality, human voice similarity or a completed audio-generation run.
"""
from __future__ import annotations
import argparse
import ast
import json
from pathlib import Path
import subprocess
import sys
import re
import os

def main() -> int:
    p=argparse.ArgumentParser()
    p.add_argument("--root",type=Path,required=True)
    p.add_argument("--voice",action="store_true")
    p.add_argument("--models",action="store_true")
    args=p.parse_args()
    root=args.root.resolve()
    errors=[]
    warnings=[]
    checks=[]
    def check(name,condition,details=""):
        checks.append({"name":name,"ok":bool(condition),"details":str(details)[:300]})
        if not condition:errors.append(f"{name}: {details}")
    def exists(relative):
        result=(root/relative).is_file()
        check("required "+relative,result)
        return result
    required=("app/studio_server.py","app/ui/index.html",
              "ACE-Step-1.5/pyproject.toml",
              "ACE-Step-1.5/uv.lock",
              "ACE-Step-1.5/.venv/Scripts/python.exe",
              "ACE-Step-1.5/.venv/Scripts/acestep.exe")
    for rel in required:exists(rel)
    versions=json.loads((root/"third_party_versions.json").read_text(encoding="utf-8"))
    for key,folder in (("ace-step","ACE-Step-1.5"),("seed-vc","Voice Engine/seed-vc"),
                       ("apexsvc","Voice Engine/alternatives/ApexSVC")):
        if key!="ace-step" and not args.voice:continue
        f=root/folder
        if not (f/".git").exists():
            check(f"git checkout {key}",False)
            continue
        x=subprocess.run(["git","-C",str(f),"rev-parse","HEAD"],capture_output=True,text=True)
        check(f"pinned SHA {key}",x.returncode==0 and x.stdout.strip()==versions[key]["commit"],
              x.stdout.strip()[:48])
    if args.voice:
        for rel in ("Voice Engine/.venv/Scripts/python.exe",
                    "Voice Engine/seed-vc/inference_studio75.py",
                    "Voice Engine/seed-vc/hf_utils.py",
                    "Voice Engine/alternatives/ApexSVC/.venv/Scripts/python.exe",
                    "Voice Engine/alternatives/ApexSVC/svc/pipeline.py"):
            exists(rel)
    # Static syntax of every published Python module: does not start any
    # server, touch user recordings or load GPU models.
    count=0
    for folder in ("app","Voice Engine","Text Engine"):
        dirpath=root/folder
        if not dirpath.exists():continue
        for file in dirpath.rglob("*.py"):
            if any(x in {".venv","seed-vc","ApexSVC","checkpoints","__pycache__"} for x in file.relative_to(root).parts):
                continue
            count+=1
            try:ast.parse(file.read_text(encoding="utf-8-sig"))
            except Exception as ex:errors.append(f"Python syntax {file.relative_to(root)}: {ex}")
    checks.append({"name":"static Python syntax","ok":True,"details":f"{count} source modules scanned"})
    # The active HTML must not point to absent local JS/CSS files.
    html=(root/"app/ui/index.html").read_text(encoding="utf-8-sig")
    for local in re.findall(r'(?:src|href)="(/[^"?#]+\.(?:js|css))',html):
        exists("app/ui/"+local.lstrip("/"))
    # Required dynamic modules in their respective isolated Python envs.
    def imports(python,modules,name):
        if not python.exists():return
        snippet=("import importlib.util,sys; import sys as _s; "
                 "missing=[x for x in sys.argv[1:] if importlib.util.find_spec(x) is None];"
                 "print(','.join(missing)); sys.exit(2 if missing else 0)")
        proc=subprocess.run([str(python),"-X","utf8","-c",snippet,*modules],capture_output=True,
                            text=True,timeout=45)
        check("import modules "+name,proc.returncode==0,
              proc.stdout.strip() or proc.stderr[-280:])
    imports(root/"ACE-Step-1.5/.venv/Scripts/python.exe",
            ["requests","gradio_client","numpy","soundfile","librosa","demucs"],"ACE/app")
    if args.voice:
        imports(root/"Voice Engine/.venv/Scripts/python.exe",
                ["torch","torchaudio","soundfile","librosa","transformers","huggingface_hub"],"SeedVC")
        imports(root/"Voice Engine/alternatives/ApexSVC/.venv/Scripts/python.exe",
                ["torch","soundfile","resampy","librosa","huggingface_hub"],"ApexSVC")
    if args.models:
        c=root/"ACE-Step-1.5/checkpoints"
        for name in ("acestep-v15-turbo","acestep-5Hz-lm-1.7B","vae","Qwen3-Embedding-0.6B"):
            folder=c/name
            check("ACE-Step model "+name,folder.is_dir() and any(folder.iterdir()) if folder.exists() else False)
        if args.voice:
            a=root/"Voice Engine/alternatives/ApexSVC/checkpoints"
            for name,minbytes in (("WavLM-Large.pt",100_000_000),("G_150k.pt",20_000_000)):
                f=a/name
                check("ApexSVC model "+name,f.is_file() and f.stat().st_size>minbytes)
            seed=root/"Voice Engine/seed-vc/checkpoints"
            for filename in ("DiT_seed_v2_uvit_whisper_base_f0_44k_bigvgan_pruned_ft_ema_v2.pth",
                             "config_dit_mel_seed_uvit_whisper_base_f0_44k.yml",
                             "rmvpe.pt","campplus_cn_common.bin"):
                found=any(seed.rglob(filename)) if seed.is_dir() else False
                check("Seed-VC model "+filename,found)
    result={"status":"passed" if not errors else "failed",
            "checks":checks,"errors":errors,"warnings":warnings,
            "voice_checked":bool(args.voice),"models_checked":bool(args.models),
            "audio_generation_tested":False,"real_voice_quality_tested":False}
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return 0 if not errors else 1

if __name__=="__main__":
    try:sys.exit(main())
    except Exception as ex:
        print(json.dumps({"status":"failed","errors":[str(ex)]},ensure_ascii=False))
        sys.exit(2)
