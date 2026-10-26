"""QA59 A/B run: 90, 180 and final 270 steps, identical QA54 source and reference.
Run AFTER training completes and frees GPU. No production installation.
"""
from pathlib import Path
import json,os,sys,subprocess,time,hashlib
R=Path.home()/"Music Studio";D=R/"Diagnostics"/"QA59";V=R/"Voice Engine";S=V/"seed-vc"
Q=R/"Diagnostics"/"QA54"
train=json.loads((D/"qa59_staged_result.json").read_text(encoding="utf-8"))
assert len(train["stages"])==2 and all(x["rc"]==0 for x in train["stages"])
run1=S/"runs"/"alex_voice_qa59_curated_270"
run2=S/"runs"/"alex_voice_qa59_stage2_181"
run3=S/"runs"/"alex_voice_qa59_stage3_270"
checkpoints={"090":next(run1.glob("DiT_epoch_*_step_00090.pth")),
             "180":next(run2.glob("DiT_epoch_*_step_00180.pth")),
             "270":run3/"ft_model.pth"}
for tag,p in checkpoints.items():
 assert p.exists() and p.stat().st_size>700_000_000,(tag,p)
src=Q/"QA54_CFG090_35s.source.wav";tgt=R/"Diagnostics"/"QA57"/"reference_selected.wav"
assert src.is_file() and tgt.is_file()
sys.path.insert(0,str(V))
from voice_guard42 import check
py=V/".venv"/"Scripts"/"python.exe"
results=[]
for tag,ckpt in checkpoints.items():
 cfg=ckpt.parent/"config_dit_mel_seed_uvit_whisper_base_f0_44k.yml"
 assert cfg.is_file()
 out=D/("qa59_infer_"+tag);out.mkdir(exist_ok=True,parents=True)
 log=D/("qa59_infer_"+tag+".log")
 command=[str(py),"-u","inference_studio51.py",
 "--source",str(src),"--target",str(tgt),"--output",str(out),
 "--checkpoint",str(ckpt),"--config",str(cfg),
 "--diffusion-steps","40","--f0-condition","True","--fp16","True",
 "--auto-f0-adjust","False","--semi-tone-shift","0",
 "--register","original","--seed","74191",
 "--acoustic-prompt-seconds","18.0","--inference-cfg-rate","0.90"]
 started=time.monotonic()
 with log.open("w",encoding="utf-8") as f:
  try:
   p=subprocess.run(command,cwd=S,stdout=f,stderr=subprocess.STDOUT,
       stdin=subprocess.DEVNULL,timeout=720)
   exitcode=p.returncode
  except subprocess.TimeoutExpired:
   exitcode=124
 result={"tag":tag,"checkpoint":str(ckpt),
  "elapsed_seconds":round(time.monotonic()-started,2),
  "exit_code":exitcode,"no_deploy":True,"same_source":True,"same_reference":True}
 audio=list(out.glob("vc_*.wav"))
 if exitcode==0 and len(audio)==1:
  report=json.loads((out/"register_report.json").read_text(encoding="utf-8"))
  audio_check=check(src,audio[0],D/("qa59_voicecheck_"+tag+".json"),"ru")
  metrics=audio_check.get("metrics",{})
  result.update(audio=str(audio[0]),speaker_proxy=report.get("speaker_embedding_cosine"),
   pitch_status=report.get("pitch_consistency",{}).get("status"),
   chunks=report.get("stitching",{}).get("diffusion_chunks"),
   drop_events=metrics.get("energy_dip_events"),
   max_dip_s=metrics.get("longest_energy_dip_s"),
   missing_vocal_fraction=metrics.get("relative_missing_vocal_frames"),
   accepted=audio_check.get("accepted"))
 else:
  result["error_log_tail"]=log.read_text(encoding="utf-8",errors="replace")[-1000:]
 print("QA59_CANDIDATE",json.dumps({k:v for k,v in result.items() if k!="error_log_tail"},ensure_ascii=True),flush=True)
 results.append(result)
 (D/"qa59_inference_results.json").write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding="utf-8")
print("QA59_CANDIDATES_COMPLETE",len(results),flush=True)
