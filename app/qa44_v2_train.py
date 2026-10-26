"""QA44 v2 single-speaker training, correct exact production base checkpoint.
Dataset only trusted user "Микрофон" files; one independent holdout. No model deploy.
"""
from pathlib import Path
import os,json,subprocess,hashlib,datetime,requests,sys
R=Path.home()/"Music Studio"
SRC=R/"Мой голос"
D=R/"Diagnostics"/"QA44"
DS=D/"train_8s_v2"
DS.mkdir(exist_ok=True,parents=True)
TRAIN=("df413d","3867cb","3ab452");HOLD="65f5f3"
SEED=R/"Voice Engine"/"seed-vc"
base=SEED/"checkpoints"/"models--Plachta--Seed-VC"/"snapshots"/"257283f9f41585055e8f858fba4fd044e5caed6e"/"DiT_seed_v2_uvit_whisper_base_f0_44k_bigvgan_pruned_ft_ema_v2.pth"
assert base.exists(),base
assert base.resolve().stat().st_size>700_000_000,base
assert not (SEED/"runs"/"alex_clean_qa44_v2"/"ft_model.pth").exists()
s=requests.Session();s.trust_env=False
h=s.get("http://127.0.0.1:7870/api/health",timeout=8).json()
assert h["job"]["status"] not in ("generating","converting","preparing")
assert not any(h.get(n,{}).get("active") for n in ("training23","training32","training41"))
items=[]
for i,ref in enumerate((*TRAIN,HOLD)):
 candidates=list(SRC.glob("*"+ref+".wav"))
 assert len(candidates)==1
 p=candidates[0]
 assert "Микрофон" in p.name and not any(q in p.name.casefold() for q in ("илья","ilya"))
 import soundfile as sf
 y,sr=sf.read(p,dtype="float32",always_2d=True)
 total=len(y)/sr
 rec={"original":p.name,"sha256":hashlib.sha256(p.read_bytes()).hexdigest(),
      "seconds":round(total,2),"role":"train" if ref in TRAIN else "holdout"}
 if ref in TRAIN:
  offsets=[0.,8.5,16.5] if total>=23 else [0.,8.5,12.0]
  if total>=29:offsets=[0.,8.,16.,23.]
  clips=[]
  for idx,t in enumerate(offsets):
   dur=min(8.5,total-t)
   if dur<3:continue
   name=f"mic{i+1}_chunk{idx+1}.wav"
   out=DS/name
   proc=subprocess.run(["ffmpeg","-nostdin","-v","error","-y","-ss",str(t),"-i",str(p),
       "-t",str(dur),"-ac","1","-ar","44100","-c:a","pcm_f32le",str(out)],
       capture_output=True,text=True,timeout=60)
   if proc.returncode:raise RuntimeError(proc.stderr[-1200:])
   assert out.stat().st_size>12000
   clips.append({"filename":name,"start":t,"seconds":round(dur,2),
                 "sha256":hashlib.sha256(out.read_bytes()).hexdigest()})
  rec["segments"]=clips
 items.append(rec)
assert len(list(DS.glob("*.wav")))==10,len(list(DS.glob("*.wav")))
manifest={"dataset":"QA44 clean-mic v2","base_model":str(base),
 "base_sha256":hashlib.sha256(base.read_bytes()).hexdigest(),"run_name":"alex_clean_qa44_v2",
 "samples":items,"one_independent_heldout_sample":True,
 "selected_by_filename_only_not_independent_speaker_authentication":True,
 "forbidden_training_sources":["илья","Моя мелодия","Запись_2"],
 "production_model_changed":False,"not_deployed":True}
(D/"qa44_v2_manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")
print("QA44_V2_VALIDATED",json.dumps([{"name":x["original"],"role":x["role"],"segments":len(x.get("segments",[]))} for x in items],ensure_ascii=True),flush=True)
ENV=os.environ.copy()
ENV.update({"PYTHONIOENCODING":"utf-8","PYTHONUTF8":"1","HF_HUB_DISABLE_TELEMETRY":"1",
 "HTTP_PROXY":"","HTTPS_PROXY":"","ALL_PROXY":"","NO_PROXY":"127.0.0.1,localhost,::1"})
exe=R/"Voice Engine"/".venv"/"Scripts"/"python.exe"
command=[str(exe),"-u",str(SEED/"train_hapych_lowvram.py"),
 "--config","configs/presets/config_dit_mel_seed_uvit_whisper_base_f0_44k.yml",
 "--pretrained-ckpt",str(base),
 "--dataset-dir",str(DS),"--run-name","alex_clean_qa44_v2",
 "--batch-size","1","--max-steps","100","--max-epochs","100",
 "--save-every","50","--num-workers","0"]
log=D/"qa44_v2_train.log"
start=__import__("time").monotonic()
with log.open("w",encoding="utf-8") as f:
 try:
  p=subprocess.run(command,cwd=str(SEED),stdout=f,stderr=subprocess.STDOUT,
      stdin=subprocess.DEVNULL,env=ENV,timeout=1400)
  ret=p.returncode
 except subprocess.TimeoutExpired:
  ret=124
model=SEED/"runs"/"alex_clean_qa44_v2"/"ft_model.pth"
r={"exit_code":ret,"seconds":round(__import__("time").monotonic()-start,1),
 "model_path":str(model),"model_available":model.is_file() and model.stat().st_size>100_000_000 if model.exists() else False,
 "train_clips":10,"holdout_original":items[-1]["original"],"deployed":False}
(D/"qa44_v2_train_result.json").write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding="utf-8")
print("QA44_V2_FINISHED",json.dumps(r,ensure_ascii=True),flush=True)
if ret:sys.exit(ret)
