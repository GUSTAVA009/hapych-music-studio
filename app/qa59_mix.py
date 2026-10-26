"""QA59 stereo A/B sample from selected model vs the exact original QA54 backing.
No re-demixing: subtract final Q54 vocal from the identical QA54 master.
Preserves original track, music, user uploads, active model.
"""
from pathlib import Path
import numpy as np,soundfile as sf,sys,json,subprocess,hashlib
R=Path.home()/"Music Studio";D=R/"Diagnostics"/"QA59";Q=R/"Diagnostics"/"QA54"
sys.path.insert(0,str(R/"Voice Engine"))
from studio_mix21 import gentle_deess,vocal_room
from studio_mix16 import declick,db,EPS
from studio_mix20 import power_frames
best=json.loads((D/"qa59_selection.json").read_text(encoding="utf-8"))
runs=json.loads((D/"qa59_inference_results.json").read_text(encoding="utf-8"))
chosen=next(x for x in runs if x["tag"]==best["selected_tag"])
assert chosen["exit_code"]==0 and Path(chosen["audio"]).is_file()
orig=json.loads((Q/"QA54_CFG090_35s.quality.json").read_text(encoding="utf-8"))
master,sr=sf.read(orig["master"],dtype="float32",always_2d=True)
voice_old,ss=sf.read(Q/"QA54_CFG090_35s.finished.wav",dtype="float32",always_2d=True)
source,sc=sf.read(Q/"QA54_CFG090_35s.source.wav",dtype="float32",always_2d=True)
voice,sn=sf.read(chosen["audio"],dtype="float32",always_2d=True)
assert sr==ss==sc==sn==44100
n=len(master);old=np.pad(voice_old.mean(axis=1),(0,max(0,n-len(voice_old))))[:n]
src=np.pad(source.mean(axis=1),(0,max(0,n-len(source))))[:n]
v=np.pad(voice.mean(axis=1),(0,max(0,n-len(voice))))[:n]
attenuation=10**(float(orig["mix"]["master_gain_db"])/20)
processed_backing=master/attenuation-vocal_room(old,sr)
rebuild=(processed_backing+vocal_room(old,sr))*attenuation
assert np.sqrt(np.mean((rebuild-master)**2))<1e-6,"Backing inversion mismatch"
v=v-np.mean(v)
v,clicks=declick(v)
v,deess=gentle_deess(v,sr)
hop=max(250,sr//100)
rr=power_frames(src,hop)
rv=power_frames(v,hop)
active=(rr>max(10**(-48/20),float(np.percentile(rr,85))*.15))&(rv>10**(-55/20))
assert active.sum()>=20
gain_db=float(np.clip(np.median(db(rr[active])-db(rv[active])),-24,18))
v*=10**(gain_db/20)
wav=D/("QA59_MyVoice_"+best["selected_tag"]+"_35s_24bit.wav")
mp3=wav.with_suffix(".mp3")
y=(processed_backing+vocal_room(v,sr))*attenuation
peak=float(np.max(np.abs(y)))
scaling=1.0 if peak<.89 else .89/max(peak,1e-8)
y*=scaling
sf.write(wav,y,sr,subtype="PCM_24")
proc=subprocess.run(["ffmpeg","-nostdin","-v","error","-y","-i",str(wav),
                     "-c:a","libmp3lame","-b:a","320k",str(mp3)],capture_output=True,text=True,timeout=90)
assert proc.returncode==0,proc.stderr[-800:]
check,scheck=sf.read(wav,dtype="float32",always_2d=True)
assert scheck==sr and not np.isnan(check).any() and check.shape[1]==2
meta={"tag":best["selected_tag"],"source_song":"QA45 Там, где тепло",
 "comparison_reference":"QA54 same 35s source music and original backing",
 "dataset":"QA59 clean 74.64s speaker-only","train_steps":int(best["selected_tag"]),
 "same_melody":True,"same_mixing_style":True,"speaker_similarity_human_verified":False,
 "accent_corrected_human_verified":False,"undamaged_words_verified":False,
 "production_originals_untouched":True,
 "gain_db":round(gain_db,3),"max_peak_dbfs":round(float(20*np.log10(max(abs(y).max(),1e-8))),2),
 "deesser":deess,"clicks_repaired":clicks,
 "wav":str(wav),"mp3":str(mp3),"bytes":mp3.stat().st_size,
 "duration_seconds":round(len(y)/sr,3),
 "hash_sha256":hashlib.sha256(mp3.read_bytes()).hexdigest()}
(D/"qa59_audio_export.json").write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding="utf-8")
print("QA59_AUDIO_READY",json.dumps(meta,ensure_ascii=True),flush=True)
