"""QA40 - gentle, isolated formant-resonance A/B master.
Uses stored vocal+master, reconstructs SAME backing and changes only processed lead.
Conservative <2 dB parametric notches, no source pitch/phoneme replacement.
Derived A/B files are diagnostics, not silently promoted to library.
"""
from pathlib import Path
import numpy as np,soundfile as sf,json,subprocess,hashlib
from scipy.signal import iirnotch,filtfilt
R=Path.home()/"Music Studio";D=R/"Diagnostics"/"QA40"
stem="QA40_MyVoice_22secRef_40steps"
master=R/"Мастер WAV"/(stem+".wav")
vocal=D/(stem+".finished.wav")
meta=json.loads((D/(stem+".quality.json")).read_text(encoding="utf-8"))
assert master.is_file() and vocal.is_file()
sysmod=__import__("sys");sysmod.path.insert(0,str(R/"Voice Engine"))
from studio_mix21 import vocal_room
m,sr=sf.read(master,dtype="float64",always_2d=True)
vv,srv=sf.read(vocal,dtype="float64",always_2d=True)
assert sr==srv==44100,(sr,srv)
v=vv.mean(axis=1)
n=len(m);v=np.pad(v,(0,max(0,n-len(v))))[:n]
attenuation=float(10**(float(meta["mix"]["master_gain_db"])/20))
backing=m/attenuation-vocal_room(v.astype("float32"),sr)
def soften(v):
 x=v.copy()
 # Harmonic peaks were measured on this sample's separated vocal. Gentle Q-band
 # attenuation is limited to 1.5 dB to retain vowels and consonant articulation.
 cuts=[(984,5,0.17),(1647,4.3,0.13),(2140,4.3,0.15),(492,7,0.07)]
 for f,q,ratio in cuts:
  b,a=iirnotch(f,q,fs=sr)
  notched=filtfilt(b,a,x,method="pad")
  x=x*(1-ratio)+notched*ratio
 return x,cuts
new,cuts=soften(v)
mixed=backing+vocal_room(new.astype("float32"),sr)
peak=float(np.max(np.abs(mixed)))
attenuation2=min(1,float(10**(-1.2/20))/max(peak,1e-8))
out=mixed*attenuation2
# These are 40s mid-song examples, so use listening fades to avoid accidental
# abrupt start/end artifact in the QA sample.
a=min(sr*.75,n//4);b=min(sr*1.4,n//4)
fade=np.ones(n,dtype=np.float64)
aa=int(a);bb=int(b)
fade[:aa]=np.sin(np.linspace(0,np.pi/2,aa))**2
fade[-bb:]=np.cos(np.linspace(0,np.pi/2,bb))**2
out*=fade[:,None]
dest=D/"QA40_MyVoice_22s_ResonanceSoftened.wav"
mp3=D/"QA40_MyVoice_22s_ResonanceSoftened_320k.mp3"
sf.write(dest,out,sr,subtype="PCM_24")
cmd=["ffmpeg","-nostdin","-y","-v","error","-i",str(dest),"-c:a","libmp3lame","-b:a","320k",str(mp3)]
p=subprocess.run(cmd,capture_output=True,text=True,timeout=100)
if p.returncode:raise RuntimeError(p.stderr[-500:])
ratio_rms=float(np.sqrt(np.mean(np.square(new-v)))/max(1e-10,np.sqrt(np.mean(np.square(v)))))
q_report={"source":str(master),"new_master":str(dest),"mp3":str(mp3),
 "notch_design":[{"center_hz":f,"q":q,"blend":a} for f,q,a in cuts],
 "modified_signal":"vocal only, exact backing reconstructed from existing master",
 "vocal_relative_rms_edit":round(ratio_rms,5),
 "peak_dbfs":round(float(20*np.log10(max(1e-8,np.max(np.abs(out))))),2),
 "listening_fades_s":[.75,1.4],
 "words_replaced":False,"pitch_modified":False,"perceptual_quality_certified":False,
 "master_sha256":hashlib.sha256(dest.read_bytes()).hexdigest(),
 "mp3_sha256":hashlib.sha256(mp3.read_bytes()).hexdigest()}
(D/"QA40_resonance_processing.json").write_text(json.dumps(q_report,ensure_ascii=False,indent=2),encoding="utf-8")
print("QA40_GENTLE_VOCAL_EQ_FINISHED",json.dumps(q_report,ensure_ascii=True),flush=True)
