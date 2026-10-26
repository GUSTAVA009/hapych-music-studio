"""QA50 sibilance-only test: preserve QA49 synth timing and melody.
Rebuild mix from exact stored QA49 master and dry vocal using same vocal room.
Remove bright hiss only on transient-dominant 4.8-9.8kHz; never de-ess
entire music, modify pitches or rewrite phonemes.
"""
from pathlib import Path
import numpy as np,soundfile as sf,json,subprocess
from scipy.signal import butter,sosfiltfilt
from scipy.ndimage import gaussian_filter1d
import sys
R=Path.home()/"Music Studio";Q=R/"Diagnostics"/"QA45";D=R/"Diagnostics"/"QA50";D.mkdir(exist_ok=True)
sys.path.insert(0,str(R/"Voice Engine"))
from studio_mix21 import vocal_room
prefix="QA49_Overlap128_Soft_35s"
meta=json.loads((Q/(prefix+".quality.json")).read_text(encoding="utf-8"))
p=Path(meta["master"]);f=Q/(prefix+".finished.wav")
assert p.exists() and f.exists()
master,sr=sf.read(p,dtype="float32",always_2d=True)
v,sv=sf.read(f,dtype="float32",always_2d=True)
assert sr==sv and sr==44100
v=v.mean(axis=1)
n=len(master);v=np.pad(v,(0,max(0,n-len(v))))[:n]
gain=10**(float(meta["mix"]["master_gain_db"])/20)
assert gain>0
# finished vocal is normalized and dynamically de-essed already, so protect
# against repeat de-essing; apply a very small selective additional effect.
vroom=vocal_room(v,sr)
backing=master/gain-vroom
band=sosfiltfilt(butter(3,[5000,9300],btype="bandpass",fs=sr,output="sos"),v).astype("float32")
hop=int(sr*.01)
m=len(v)//hop
r=np.sqrt(np.mean(v[:m*hop].reshape(m,hop)**2,axis=1)+1e-12)
br=np.sqrt(np.mean(band[:m*hop].reshape(m,hop)**2,axis=1)+1e-12)
ratio=br/(r+1e-8)
# only bright sustained hiss with weaker vowel fundamental
mask=(ratio>.53)&(r>max(.0018,np.percentile(r,75)*.13))
attack=gaussian_filter1d(mask.astype(float),sigma=3)
reduction=np.clip((ratio-.53)/.35,0,1)*attack*2.0
reduction=gaussian_filter1d(reduction,3)
g=np.interp(np.arange(n)/hop,np.arange(m),10**(-reduction/20),left=1,right=1)
softer=v+band*(g-1)
newmix=(backing+vocal_room(softer.astype("float32"),sr))*gain
peak=np.max(np.abs(newmix))
if peak>.89:newmix*=.89/peak
fade=np.ones(n)
t=int(sr*.12);end=int(sr*.3)
fade[:t]=np.sin(np.linspace(0,np.pi/2,t))**2
fade[-end:]=np.cos(np.linspace(0,np.pi/2,end))**2
# NOTE: QA49 full 35s clip started mid-song; listening fades added at cut boundaries.
newmix*=fade[:,None]
wav=D/"QA50_QA49_Deess_A_B_35s.wav";mp3=wav.with_suffix(".mp3")
sf.write(wav,newmix,sr,subtype="PCM_24")
cmd=["ffmpeg","-nostdin","-v","error","-y","-i",str(wav),"-c:a","libmp3lame","-b:a","320k",str(mp3)]
p=subprocess.run(cmd,capture_output=True,text=True,timeout=90)
assert p.returncode==0,p.stderr
out={"source":prefix,"target":"sibilance only, preserving original seeded VC, same stems",
"peak_additional_reduction_db":round(float(reduction.max()),3),"affected_hiss_frames":int((reduction>.3).sum()),
"pronunciation_corrected":False,"dropout_repaired":False,"no_pitches_modified":True,
"new_mp3":str(mp3),"new_wav":str(wav),
"reference_sources_intact":True}
(D/"qa50_deess_report.json").write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding="utf-8")
print("QA50_MIX_READY",json.dumps(out,ensure_ascii=True),flush=True)
