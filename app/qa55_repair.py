"""QA55 targeted vowel continuity correction without new artificial vocals.
On QA54 decoded output only. Restoration envelope is source-anchored and
restricted to confirmed weak-frame regions; no source voice mixing.
The process cannot change wrong phonemes, and is a non-deployed experiment.
"""
from pathlib import Path
import json,numpy as np,soundfile as sf,subprocess,sys
from scipy.ndimage import gaussian_filter1d
R=Path.home()/"Music Studio";D=R/"Diagnostics"/"QA55";D.mkdir(parents=True,exist_ok=True)
Q=R/"Diagnostics"/"QA54";stem="QA54_CFG090_35s"
q=json.loads((Q/(stem+".quality.json")).read_text(encoding="utf-8"))
from pathlib import Path
sys.path.insert(0,str(R/"Voice Engine"))
from studio_mix21 import vocal_room
x,sr=sf.read(Q/(stem+".finished.wav"),dtype="float32",always_2d=True)
source,sr2=sf.read(Q/(stem+".source.wav"),dtype="float32",always_2d=True)
master,sr3=sf.read(q["master"],dtype="float32",always_2d=True)
assert sr==sr2==sr3==44100
v=x.mean(axis=1);src=source.mean(axis=1)
n=min(len(v),len(src),len(master));v=v[:n];src=src[:n];master=master[:n]
hop=int(sr*.010);frames=n//hop
def energy(y):
 return np.sqrt(np.mean(y[:frames*hop].reshape(frames,hop).astype(np.float64)**2,axis=1)+1e-12)
r=energy(src);s=energy(v)
# Source may have different loudness, so match reference/source ratio to local
# converted acoustic median rather than globally imposing source performance.
relative=20*np.log10((r+1e-6)/(s+1e-6))
baseline=gaussian_filter1d(relative,40)
residual=relative-baseline
residual=gaussian_filter1d(residual,9)
# Repairs only when reference is loudly active and converted vowel is weak;
# broad onset changes and correct consonant silences stay intact.
active=r>max(.003,float(np.percentile(r,80))*.17)
windows=np.arange(frames)*.01
scope=((windows>=16.4)&(windows<=33.1))
lost=(residual>3.0)&(active)&scope
# Unvoiced consonants often produce elevated ratio; only repair if enough
# consecutive 10ms frames and never treat isolated plosive as a sustained vowel.
from scipy.ndimage import binary_opening,binary_closing
mask=binary_closing(binary_opening(lost,structure=np.ones(5)),structure=np.ones(7))
amount=np.clip((residual-3)*.32,0,3.0)
amount=gaussian_filter1d(amount*mask,8)
# Conservative 3dB max, enforce <=0.10 dB per 10ms change.
g=np.minimum(3.0,np.maximum(0.0,amount))
for i in range(1,len(g)):g[i]=min(g[i],g[i-1]+.10)
for i in range(len(g)-2,-1,-1):g[i]=min(g[i],g[i+1]+.10)
t=np.arange(n)/hop
linear=np.interp(t,np.arange(frames),10**(g/20),left=1,right=1)
fixed=v*linear.astype(np.float32)
# Use exact unchanged backing reconstructed by subtracting the original finished vocal
# from the existing master, no re-mastering or repeated de-essing.
backing=master-vocal_room(v,sr)*10**(float(q["mix"]["master_gain_db"])/20)
new=(backing+vocal_room(fixed,sr)*10**(float(q["mix"]["master_gain_db"])/20))
peak=float(np.max(abs(new)))
if peak>.96:new*=.96/peak
wav=D/"QA55_Dorogi_Toropit_ContinuityAB.wav"
mp3=D/"QA55_Dorogi_Toropit_ContinuityAB.mp3"
sf.write(wav,new,sr,subtype="PCM_24")
cmd=["ffmpeg","-y","-hide_banner","-loglevel","error","-nostdin","-i",str(wav),"-c:a","libmp3lame","-b:a","320k",str(mp3)]
p=subprocess.run(cmd,capture_output=True,text=True,timeout=120)
assert p.returncode==0,p.stderr[-1000:]
changes=[]
indices=np.where(g>.15)[0]
for i in indices:
 if not changes or i>changes[-1][-1]+1:changes.append([i])
 else:changes[-1].append(i)
segs=[{"start_s":round(b[0]*.01,2),"end_s":round((b[-1]+1)*.01,2),"peak_gain_db":round(float(max(g[b])),2)} for b in changes]
quality={"original":"QA54 CFG 0.90","target_words":["дороги","торопить"],
 "method":"source-anchored soft-envelope bridging; no source audio splicing",
 "maximum_gain_db":round(float(g.max()),3),"corrected_segments":segs,
 "original_timbre_replaced":False,"phoneme_reconstruction":False,
 "word_pronunciation_verified":False,"source_unchanged":True,
 "master_out":str(wav),"mp3_out":str(mp3),"duration_s":round(n/sr,2),
 "edited_vocal_rms_ratio":round(float(np.sqrt(np.mean((fixed-v)**2))/max(np.sqrt(np.mean(v*v)),1e-6)),5)}
(D/"qa55_report.json").write_text(json.dumps(quality,ensure_ascii=False,indent=2),encoding="utf-8")
print("QA55_AUDIO_CREATED",json.dumps(quality,ensure_ascii=True),flush=True)
