"""QA59 held-out A/B: previous QA44 vs selected QA59, independent user mic file
excluded from ALL training clips. Source and settings identical.
Nothing is installed in live Music Studio.
"""
from pathlib import Path
import json,subprocess,time,os,sys
R=Path.home()/"Music Studio";D=R/"Diagnostics"/"QA59";V=R/"Voice Engine";S=V/"seed-vc";Q=R/"Diagnostics"/"QA54"
best=json.loads((D/"qa59_selection.json").read_text(encoding="utf-8"))
assert best["selected_tag"] in ["090","180","270"]
selected=next(e for e in json.loads((D/"qa59_inference_results.json").read_text(encoding="utf-8")) if e["tag"]==best["selected_tag"])
assert selected["exit_code"]==0 and Path(selected["checkpoint"]).is_file()
code="65f5f3"
original=next((R/"Мой голос").glob("*"+code+".wav"))
manifest=json.loads((D/"qa59_dataset_manifest.json").read_text(encoding="utf-8"))
assert original.name in manifest["heldout_files"]
assert all(original.name!=s["source_file"] for s in manifest["segments"])
sys.path.insert(0,str(V))
from convert_track_studio54_cfg090 import reference_excerpt
work=D/"holdout_reference";work.mkdir(exist_ok=True,parents=True)
ref,refmeta=reference_excerpt(original,work)
assert 8<refmeta["seconds"]<15
source=Q/"QA54_CFG090_35s.source.wav"
assert source.is_file()
py=V/".venv"/"Scripts"/"python.exe"
old=S/"runs"/"alex_clean_qa44_v2"
new=S/"runs"/"alex_voice_qa59_curated_270"
experiments=[
  ("QA44_previous",old/"ft_model.pth",old/"config_dit_mel_seed_uvit_whisper_base_f0_44k.yml"),
  ("QA59_"+best["selected_tag"],Path(selected["checkpoint"]),new/"config_dit_mel_seed_uvit_whisper_base_f0_44k.yml")
]
for _,ck,cfg in experiments:assert ck.is_file() and cfg.is_file()
from voice_guard42 import check
results=[]
for label,ckpt,cfg in experiments:
 out=D/("holdout_"+label);out.mkdir(parents=True,exist_ok=True)
 cmd=[str(py),"-u","inference_studio51.py","--source",str(source),"--target",str(ref),
   "--output",str(out),"--checkpoint",str(ckpt),"--config",str(cfg),
   "--diffusion-steps","40","--f0-condition","True","--fp16","True",
   "--auto-f0-adjust","False","--semi-tone-shift","0","--register","original",
   "--seed","74191","--acoustic-prompt-seconds","18.0","--inference-cfg-rate","0.90"]
 t=time.monotonic()
 with (D/("qa59_holdout_"+label+".log")).open("w",encoding="utf-8") as f:
  try:ret=subprocess.run(cmd,cwd=S,stdout=f,stderr=subprocess.STDOUT,
                 stdin=subprocess.DEVNULL,timeout=700).returncode
  except subprocess.TimeoutExpired:ret=124
 files=list(out.glob("vc_*.wav"))
 rr={"variant":label,"trained_on_holdout":False,"exit":ret,"elapsed_s":round(time.monotonic()-t,2)}
 if ret==0 and len(files)==1:
  report=json.loads((out/"register_report.json").read_text(encoding="utf-8"))
  checks=check(source,files[0],D/("qa59_holdout_voicecheck_"+label+".json"),"ru")
  metrics=checks["metrics"]
  rr.update(speaker_proxy=report.get("speaker_embedding_cosine"),
   missing_fraction=metrics.get("relative_missing_vocal_frames"),
   drop_events=metrics.get("energy_dip_events"),
   longest_dip=metrics.get("longest_energy_dip_s"),
   pitch_status=report.get("pitch_consistency",{}).get("status"),
   audio=str(files[0]))
 results.append(rr)
 (D/"qa59_holdout_results.json").write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding="utf-8")
 print("QA59_HOLDOUT",json.dumps(rr,ensure_ascii=True),flush=True)
