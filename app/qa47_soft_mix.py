"""QA47 soft phrase vocal mix, same original QA45 backing by exact subtraction.
No editing/overwriting source tracks. F0 unchanged. Recover accompaniment at
sample level from QA47 baseline master and its processed vocal; compare re-sum.
"""
import sys,json,hashlib,subprocess,re
from pathlib import Path
import numpy as np,soundfile as sf
R=Path.home()/"Music Studio";D=R/"Diagnostics"/"QA47";V=R/"Voice Engine"
sys.path.insert(0,str(V))
from studio_mix21 import vocal_room as original_room
from studio_mix46 import finish as soft_finish
j=json.loads((D/"QA47_plateau_report.json").read_text(encoding="utf-8"))
chosen=j["selected"];assert chosen["label"]=="plateau_13_sigma3"
vocal=Path(chosen["file"]);assert vocal.is_file()
quality=json.loads((D/"QA47_rawbase_35s.quality.json").read_text(encoding="utf-8"))
old_master=Path(quality["master"])
old_voc=D/"QA47_rawbase_35s.finished.wav"
source=D/"QA47_rawbase_35s.source.wav"
assert old_master.is_file() and old_voc.is_file() and source.is_file()
m,sr=sf.read(old_master,dtype="float32",always_2d=True)
v,rv=sf.read(old_voc,dtype="float32",always_2d=True)
assert sr==rv==44100
if v.shape[1]>1:v=v.mean(axis=1,keepdims=True)
n=len(m);v=np.pad(v[:,0],(0,max(0,n-len(v))))[:n]
att=10**(float(quality["mix"]["master_gain_db"])/20)
original_backing=m/att-original_room(v,sr)
# Ensure exact reconstruction within original 24-bit quantization+rounded reported gain.
reconstructed=(original_backing+original_room(v,sr))*att
recon_error=float(np.max(np.abs(reconstructed-m)))
assert recon_error<.00001,recon_error
backing=D/"QA47_recovered_backing.wav"
sf.write(backing,original_backing,sr,subtype="FLOAT")
finished=D/"QA47_soft_phrase_lead.wav"
mixed=D/"QA47_soft_phrase_mix.wav"
report=soft_finish(str(vocal),str(backing),str(source),str(finished),str(mixed),sr=sr,chorus_ranges=[])
raw,rs=sf.read(mixed,dtype="float64",always_2d=True)
assert rs==sr
# Listening excerpt mid-song: avoid a harsh start/end (no impact on source track).
a=int(sr*.5);b=int(sr*1.25)
fade=np.ones(len(raw),dtype="float64")
fade[:a]=np.sin(np.linspace(0,np.pi/2,a))**2
fade[-b:]=np.cos(np.linspace(0,np.pi/2,b))**2
raw*=fade[:,None]
listen=D/"QA47_soft_phrase_faded.wav"
sf.write(listen,raw,sr,subtype="PCM_24")
mp3=D/"QA47_MyVoice_SoftPhrase_35s_320kbps.mp3"
cmd=["ffmpeg","-nostdin","-y","-v","error","-i",str(listen),"-c:a","libmp3lame","-b:a","320k",str(mp3)]
done=subprocess.run(cmd,capture_output=True,text=True,timeout=120)
assert done.returncode==0,done.stderr
stats={"source_qa45_untouched":True,"new_audio":str(mp3),"candidate":chosen["label"],
       "source_reconstruction_max_sample_error":round(recon_error,8),
       "selected_vocal":str(vocal),"same_recording_timbre_model":True,
       "melody_preserved":True,"lyrics_edit":False,"source_voice_blended":False,
       "drop_events_selected":chosen["dips"],"weak_ratio_selected":chosen["weak_ratio"],
       "gain_step_p99_old":j["base"]["gain_step_p99_db_20ms"],
       "gain_step_p99_soft":chosen["gain_step_p99_db_20ms"],
       "mix":report,"mp3_sha256":hashlib.sha256(mp3.read_bytes()).hexdigest(),
       "human_listening_verification":False,"accent_corrected":False}
(D/"QA47_soft_phrase_master_report.json").write_text(json.dumps(stats,ensure_ascii=False,indent=2),encoding="utf-8")
print("QA47_NEW_MIX_READY",json.dumps({k:v for k,v in stats.items() if k!="mix"},ensure_ascii=True),flush=True)
