"""QA66 targeted ablation of CFM source/prompt context in Seed-VC.
No retraining, no changes to production or singer library.
Compare 8s vs 12s reference acoustics vs QA54 18s reference.
"""
from pathlib import Path
import time,os,json,subprocess,sys,requests,hashlib
R=Path.home()/"Music Studio";D=R/"Diagnostics"/"QA66";D.mkdir(parents=True,exist_ok=True)
V=R/"Voice Engine";S=V/"seed-vc"
src=R/"Diagnostics"/"QA54"/"QA54_CFG090_35s.source.wav"
ref=R/"Diagnostics"/"QA57"/"reference_selected.wav"
cp=S/"runs"/"alex_clean_qa44_v2"/"ft_model.pth"
cfg=S/"runs"/"alex_clean_qa44_v2"/"config_dit_mel_seed_uvit_whisper_base_f0_44k.yml"
assert all(p.is_file() for p in [src,ref,cp,cfg])
client=requests.Session();client.trust_env=False
h=client.get("http://127.0.0.1:7870/api/health",timeout=8).json()
assert h["ready"] and h["job"]["status"] not in ("preparing","generating","converting")
args=[str(V/".venv"/"Scripts"/"python.exe"),"-u","inference_studio51.py",
 "--source",str(src),"--target",str(ref),"--checkpoint",str(cp),"--config",str(cfg),
 "--diffusion-steps","40","--f0-condition","True","--fp16","True",
 "--auto-f0-adjust","False","--semi-tone-shift","0",
 "--register","original","--seed","74191","--inference-cfg-rate","0.90"]
env=os.environ.copy()
env.update(PYTHONUTF8="1",PYTHONIOENCODING="utf-8",HF_HUB_OFFLINE="1",NO_PROXY="localhost,127.0.0.1,::1",no_proxy="localhost,127.0.0.1,::1")
results=[]
for duration in (8.,12.):
 name=str(int(duration))+"sec"
 path=D/("prompt_"+name)
 assert not path.exists(),"Do not overwrite previous trial: "+str(path)
 log=D/("qa66_infer_"+name+".log")
 cmd=args+["--output",str(path),"--acoustic-prompt-seconds",str(duration)]
 print("START_QA66",name,flush=True)
 started=time.monotonic()
 with log.open("w",encoding="utf-8") as f:
  try:
   rc=subprocess.run(cmd,cwd=S,env=env,stdout=f,stderr=subprocess.STDOUT,
           stdin=subprocess.DEVNULL,timeout=650).returncode
  except subprocess.TimeoutExpired:rc=124
 audio=list(path.glob("vc_*.wav"))
 report=json.loads((path/"register_report.json").read_text(encoding="utf-8")) if (path/"register_report.json").exists() else {}
 item={"name":name,"exit_code":rc,"elapsed_s":round(time.monotonic()-started,1),
       "prompt_sec":duration,"source_reference_identical":True,
       "checkpoint_qa54":True,"model_unchanged":True,
       "audio":str(audio[0]) if len(audio)==1 else None,
       "chunks":report.get("stitching",{}).get("diffusion_chunks"),
       "chunk_starts_frames":report.get("stitching",{}).get("chunk_starts_frames"),
       "speaker_cosine":report.get("speaker_embedding_cosine"),
       "pitch_status":report.get("pitch_consistency",{}).get("status"),
       "f0_cleanup":report.get("f0_cleanup"),
       "error_log_tail":log.read_text(encoding="utf-8",errors="replace")[-1300:] if rc!=0 else None}
 results.append(item)
 (D/"qa66_generation_report.json").write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding="utf-8")
 print("QA66_TRIAL",json.dumps({k:v for k,v in item.items() if k not in ("error_log_tail","f0_cleanup")},ensure_ascii=True),flush=True)
 if rc!=0:sys.exit(rc)
print("QA66_ALL_TRIALS_READY",len(results),flush=True)
