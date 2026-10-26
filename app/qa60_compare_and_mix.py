"""QA60: check untrained Seed-VC against QA54; same track and same backing.
Original QA54 untouched. Only staged Diagnostics/QA60 files.
"""
from pathlib import Path
import json,numpy as np,soundfile as sf,sys,subprocess,hashlib
R=Path.home()/"Music Studio";D=R/"Diagnostics"/"QA60";Q=R/"Diagnostics"/"QA54"
sys.path.insert(0,str(R/"Voice Engine"))
from voice_guard42 import check
from studio_mix21 import gentle_deess,vocal_room
from studio_mix16 import declick,db
from studio_mix20 import power_frames
q=json.loads((Q/"QA54_CFG090_35s.quality.json").read_text(encoding="utf-8"))
base=next((D/"base_inference").glob("vc_*.wav"))
source=Q/"QA54_CFG090_35s.source.wav"
result=check(source,base,D/"qa60_base_vocal_integrity.json","ru")
main,sr=sf.read(q["master"],dtype="float32",always_2d=True)
prior,p_sr=sf.read(Q/"QA54_CFG090_35s.finished.wav",dtype="float32",always_2d=True)
converted,cr=sf.read(base,dtype="float32",always_2d=True)
origin,orig_sr=sf.read(source,dtype="float32",always_2d=True)
assert sr==p_sr==cr==orig_sr==44100
n=len(main)
def fit(x):
 y=x.mean(axis=1)
 if len(y)<n:return np.pad(y,(0,n-len(y)))
 return y[:n]
vold=fit(prior);vnew=fit(converted);vsrc=fit(origin)
master_gain=10**(float(q["mix"]["master_gain_db"])/20)
music=main/master_gain-vocal_room(vold,sr)
vnew=np.asarray(vnew-np.mean(vnew),dtype="float32")
vnew,clicks=declick(vnew)
vnew,deesser=gentle_deess(vnew,sr)
hop=max(250,sr//100)
a=power_frames(vsrc,hop);b=power_frames(vnew,hop)
mask=(a>max(10**(-48/20),float(np.percentile(a,85))*.15))&(b>10**(-55/20))
assert mask.sum()>=20
gain_db=float(np.clip(np.median(db(a[mask])-db(b[mask])),-24,18))
vnew*=10**(gain_db/20)
out=(music+vocal_room(vnew,sr))*master_gain
peak=float(abs(out).max())
out*=min(1.0,.89/max(peak,1e-8))
wav=D/"QA60_BaseSeedVC_35s_24bit.wav";mp3=D/"QA60_BaseSeedVC_35s_320kbps.mp3"
sf.write(wav,out,sr,subtype="PCM_24")
p=subprocess.run(["ffmpeg","-nostdin","-v","error","-y","-i",str(wav),"-c:a","libmp3lame","-b:a","320k",str(mp3)],
 capture_output=True,text=True,timeout=90)
assert p.returncode==0,p.stderr[-600:]
v=json.loads((D/"base_inference"/"register_report.json").read_text(encoding="utf-8"))
quality={"title":"QA60 untrained official Seed-VC vs QA54 personal","same_source_and_reference":True,
"same_seed_and_steps_and_cfg":True,"same_backing_master":True,
"cosine":v.get("speaker_embedding_cosine"),
"QA54_cosine":q.get("speaker_embedding_cosine"),
"base_voice_check":result.get("metrics"),
"qa54_voice_check":q["voice_check"]["metrics"],"base_pitch_status":v.get("pitch_consistency",{}).get("status"),
"qa54_pitch_status":q.get("pitch_consistency",{}).get("status"),
"gain_db":round(gain_db,2),"deesser":deesser,"declick":clicks,
"output":str(mp3),"sha256":hashlib.sha256(mp3.read_bytes()).hexdigest(),
"correct_pronunciation_not_proven":True,"not_deployed":True}
(D/"qa60_base_comparison.json").write_text(json.dumps(quality,ensure_ascii=False,indent=2),encoding="utf-8")
print("QA60_BASE_COMPARE",json.dumps({k:v for k,v in quality.items() if k not in ("deesser","declick","sha256")},ensure_ascii=True),flush=True)
