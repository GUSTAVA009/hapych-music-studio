"""Quarantine unverified speakers and contaminated old personal training.
Reversible same-disk moves; does not touch user music or clean microphone files.
"""
from pathlib import Path
import json,shutil,requests,datetime,hashlib,os
R=Path.home()/"Music Studio";OUT=R/"Voice Quarantine"/"QA36_20261024"
M=R/"Мой голос"
TRAIN=R/"Voice Engine"/"training_dataset"
RUN=R/"Voice Engine"/"seed-vc"/"runs"/"music_studio_personal_v1"
s=requests.Session();s.trust_env=False
h=s.get("http://127.0.0.1:7870/api/health",timeout=8).json()
if h.get("job",{}).get("status") in ("preparing","generating","converting") or any(h.get(x,{}).get("active") for x in ("training32","training41","training23")):
 raise RuntimeError("Active audio job, refusing to modify voice library")
if __import__("sys").modules.get("psutil"):
 pass
import sys
sys.path.insert(0,str(R/"app"))
import voice_training
if voice_training.status()["active"]:raise RuntimeError("Voice fine-tune active")
manifest=json.loads((TRAIN/"ALEX_KZNT"/"dataset_manifest.json").read_text(encoding="utf-8"))
if not any("илья" in x["source"].lower() for x in manifest["samples"]):
 raise RuntimeError("Legacy contamination evidence not found, abort for safety")
sources=[]
for f in M.iterdir():
 if f.is_file() and f.suffix.lower() in (".wav",".mp3",".m4a",".flac",".ogg",".aac"):
  # User-recorded microphone WAVs stay; imported melody/short other reference does not.
  if "Микрофон" not in f.name:sources.append(f)
sources.extend([TRAIN/"ALEX_KZNT",TRAIN/"ALEX_KZNT_SHORT",RUN])
OUT.mkdir(parents=True,exist_ok=True)
record={"date":datetime.datetime.now().isoformat(),"reason":"Exclude unverified voices, including Ilya legacy dataset",
        "server_before":h["job"]["status"],"actions":[],"reversible":True,
        "original_mic_wavs_preserved":True,"old_personal_checkpoint_disabled":True}
for f in sources:
 if not f.exists():continue
 dest=OUT/("legacy_"+f.name if f.is_dir() else "unverified_"+f.name)
 if dest.exists():raise RuntimeError("Quarantine collision: "+str(dest))
 item={"original":str(f),"quarantine":str(dest),"was_directory":f.is_dir(),
       "bytes":sum(x.stat().st_size for x in f.rglob("*") if x.is_file()) if f.is_dir() else f.stat().st_size}
 record["actions"].append(item)
# Before moving anything, write a restore manifest
(OUT/"restore_manifest.json").write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding="utf-8")
for item in record["actions"]:
 p=Path(item["original"]);q=Path(item["quarantine"])
 if not p.exists():raise RuntimeError("Source vanished: "+str(p))
 os.replace(p,q)  # atomic same NTFS volume
print(json.dumps({"quarantined":[{"original":Path(x["original"]).name,"bytes":x["bytes"]} for x in record["actions"]],
                  "active_voices":[p.name for p in M.iterdir() if p.is_file() and p.suffix.lower() in (".wav",".mp3",".m4a",".flac",".ogg",".aac")],
                  "personal_model_exists":RUN.exists(),
                  "restore_manifest":str(OUT/"restore_manifest.json")},ensure_ascii=True))
