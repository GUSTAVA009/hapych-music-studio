"""QA44 clean single-speaker pilot; not auto-deployed.
Three mic-only samples for training, one short mic-only holdout.
All sources and production checkpoints are unchanged.
"""
from pathlib import Path
import os,json,subprocess,hashlib,datetime,requests,sys
R=Path.home()/"Music Studio"
VOICES=R/"Мой голос"
WORK=R/"Diagnostics"/"QA44"
DATA=WORK/"train_clean_only"
DATA.mkdir(parents=True,exist_ok=True)
ID_TRAIN=("df413d","3867cb","3ab452")
ID_HOLDOUT="65f5f3"
s=requests.Session();s.trust_env=False
health=s.get("http://127.0.0.1:7870/api/health",timeout=8).json()
if health["job"]["status"] in ("generating","preparing","converting") or any(health.get(k,{}).get("active") for k in ("training23","training32","training41")):
 raise RuntimeError("Studio is busy")
samples=[]
for i,part in enumerate((*ID_TRAIN,ID_HOLDOUT)):
 hits=list(VOICES.glob("*"+part+".wav"))
 if len(hits)!=1:raise RuntimeError("One source record missing "+part)
 p=hits[0]
 assert "Микрофон" in p.name and "илья" not in p.name.casefold()
 sha=hashlib.sha256(p.read_bytes()).hexdigest()
 item={"original":str(p),"original_sha256":sha,"train":part in ID_TRAIN}
 if item["train"]:
  out=DATA/("clean_mic_"+str(i+1)+".wav")
  c=subprocess.run(["ffmpeg","-nostdin","-v","error","-y","-i",str(p),
    "-t","29.2","-ar","44100","-ac","1","-c:a","pcm_f32le",str(out)],
    capture_output=True,text=True,timeout=90)
  if c.returncode:raise RuntimeError("ffmpeg error "+c.stderr[-800:])
  probe=subprocess.run(["ffprobe","-v","error","-show_entries","format=duration",
    "-of","default=noprint_wrappers=1:nokey=1",str(out)],capture_output=True,text=True,timeout=20)
  seconds=float(probe.stdout)
  assert 3<seconds<29.8
  item.update(train_file=str(out),train_seconds=round(seconds,3),train_sha256=hashlib.sha256(out.read_bytes()).hexdigest())
 samples.append(item)
data={"created":datetime.datetime.now().isoformat(),
  "sources":samples,"training_count":3,"holdout_count":1,
  "speaker_metadata":"User-supplied microphone-labelled recordings. Speaker identity of each file cannot be automatically certified.",
  "excluded":["илья.m4a","Моя мелодия","Запись_2"],
  "run_name":"alex_clean_qa44","base_checkpoint_unchanged":True,
  "not_deployed":True,"no_auto_user_track_modification":True}
(WORK/"QA44_dataset_manifest.json").write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8")
print("QA44_DATASET_VALID",json.dumps([{"name":Path(x["original"]).name,"seconds":x.get("train_seconds"),"train":x["train"]} for x in samples],ensure_ascii=True),flush=True)
assert len(list(DATA.glob("*.wav")))==3
SEED=R/"Voice Engine"/"seed-vc"
PY=R/"Voice Engine"/".venv"/"Scripts"/"python.exe"
log=WORK/"qa44_training.log"
command=[str(PY),"-u",str(SEED/"train_hapych_lowvram.py"),
 "--config","configs/presets/config_dit_mel_seed_uvit_whisper_base_f0_44k.yml",
 "--dataset-dir",str(DATA),"--run-name","alex_clean_qa44",
 "--batch-size","1","--max-steps","100","--max-epochs","110",
 "--save-every","50","--num-workers","0"]
os.environ["HF_HUB_DISABLE_TELEMETRY"]="1"
os.environ["NO_PROXY"]="localhost,127.0.0.1,::1"
os.environ["no_proxy"]="localhost,127.0.0.1,::1"
with log.open("w",encoding="utf-8") as f:
 p=subprocess.run(command,cwd=SEED,stdout=f,stderr=subprocess.STDOUT,
                  stdin=subprocess.DEVNULL,timeout=1900)
out=SEED/"runs"/"alex_clean_qa44"/"ft_model.pth"
r={"exit_code":p.returncode,"model_ready":out.is_file() and out.stat().st_size>10000000 if out.exists() else False,
   "model_path":str(out),"bytes":out.stat().st_size if out.exists() else 0,
   "log":str(log),"training_samples":3,"holdout_samples":1,"deployed":False}
(WORK/"qa44_training_result.json").write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding="utf-8")
print("QA44_TRAIN_FINISHED",json.dumps(r,ensure_ascii=True),flush=True)
if p.returncode:sys.exit(p.returncode)
