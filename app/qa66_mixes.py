"""QA66 identical-backing listening mixes for 8s and 12s acoustic prompt.
Uses QA54 backing reconstruction and legacy constant normalization / vocal room.
Writes solely Diagnostics/QA66; originals and production unchanged.
"""
from pathlib import Path
import numpy as np,soundfile as sf,sys,json,subprocess,hashlib
R=Path.home()/"Music Studio";D=R/"Diagnostics"/"QA66";Q=R/"Diagnostics"/"QA54"
sys.path.insert(0,str(R/"Voice Engine"))
from studio_mix21 import gentle_deess,vocal_room
from studio_mix16 import declick,db
from studio_mix20 import power_frames
from voice_guard42 import check
baseline=json.loads((Q/"QA54_CFG090_35s.quality.json").read_text(encoding="utf-8"))
mix,sr=sf.read(baseline["master"],dtype="float32",always_2d=True)
old,s_old=sf.read(Q/"QA54_CFG090_35s.finished.wav",dtype="float32",always_2d=True)
source,s_orig=sf.read(Q/"QA54_CFG090_35s.source.wav",dtype="float32",always_2d=True)
assert sr==s_old==s_orig==44100
n=len(mix)
def fit(data):
 x=data.mean(axis=1)
 return np.pad(x,(0,max(0,n-len(x))))[:n]
x_old=fit(old);x_source=fit(source)
base_gain=10**(float(baseline["mix"]["master_gain_db"])/20)
backing=mix/base_gain-vocal_room(x_old,sr)
# Sanity check reconstruction identity within roundoff
assert np.sqrt(np.mean(((backing+vocal_room(x_old,sr))*base_gain-mix)**2))<.00001
hop=sr//100
results=[]
for inp in json.loads((D/"qa66_generation_report.json").read_text(encoding="utf-8")):
 assert inp["exit_code"]==0
 v,fs=sf.read(inp["audio"],dtype="float32",always_2d=True)
 assert fs==sr and abs(len(v)-n)/sr<.15
 tag=inp["name"]
 raw_report=check(Q/"QA54_CFG090_35s.source.wav",Path(inp["audio"]),D/("qa66_guard_"+tag+".json"),"ru")
 y=fit(v);y=y-np.mean(y)
 y,clicks=declick(y)
 y,ds=gentle_deess(y,sr)
 r=power_frames(x_source,hop);s=power_frames(y,hop)
 mask=(r>max(10**(-48/20),float(np.percentile(r,85))*.15))&(s>10**(-55/20))
 assert mask.sum()>20
 gain_db=float(np.clip(np.median(db(r[mask])-db(s[mask])),-24,18))
 y*=10**(gain_db/20)
 finished=(backing+vocal_room(y,sr))*base_gain
 peak=float(abs(finished).max())
 finished*=min(1,.89125/max(peak,1e-9))
 wav=D/("QA66_Prompt"+tag+"_35s_MASTER_24bit.wav")
 mp3=D/("QA66_Prompt"+tag+"_35s_320kbps.mp3")
 sf.write(wav,finished,sr,subtype="PCM_24")
 enc=subprocess.run(["ffmpeg","-nostdin","-v","error","-y","-i",str(wav),
 "-c:a","libmp3lame","-b:a","320k",str(mp3)],capture_output=True,text=True,timeout=120)
 assert enc.returncode==0,enc.stderr[-1000:]
 check_audio,chk_sr=sf.read(wav,dtype="float32",always_2d=True)
 assert chk_sr==sr and not np.isnan(check_audio).any() and check_audio.shape==(n,2)
 info={"variant":tag,"seconds":round(n/sr,2),"inference_seam_count":inp["chunks"]-1,
       "same_source_song_same_music_same_reference":True,
       "same_QA54_personal_weights":True,"same_f0_pitch":True,
       "audio_guard":raw_report["metrics"],
       "same_postprocessing_recipe":True,"gain_db":round(gain_db,2),
       "peak_dbfs":round(20*np.log10(max(float(abs(finished).max()),1e-8)),2),
       "mp3":str(mp3),"wav":str(wav),
       "mp3_bytes":mp3.stat().st_size,
       "mp3_sha256":hashlib.sha256(mp3.read_bytes()).hexdigest(),
       "production_not_modified":True,
       "owner_voice_naturalness_not_verified":True}
 results.append(info)
 print("QA66_LISTENING_READY",json.dumps(info,ensure_ascii=True),flush=True)
(D/"qa66_master_comparison.json").write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding="utf-8")
