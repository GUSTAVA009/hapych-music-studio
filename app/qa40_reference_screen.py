"""QA40 reference audio screening (read-only).
Prints durations, clipping, RMS, silence proportion, and 12s vs 22s candidates.
Does not identify a speaker or claim clean-only voice.
"""
import numpy as np,subprocess,json
from pathlib import Path
import scipy.signal as ss
R=Path.home()/"Music Studio";v=R/"Мой голос"
def describe(y,sr):
 peak=float(np.max(np.abs(y)))
 rms=float(np.sqrt(np.mean(y*y)+1e-12))
 frames=y[:(len(y)//int(sr*.020))*int(sr*.020)].reshape(-1,int(sr*.020))
 frame_rms=np.sqrt(np.mean(frames**2,axis=1)+1e-12)
 floor=float(np.percentile(frame_rms,10));speech=float(np.percentile(frame_rms,90))
 noise_rel_db=float(20*np.log10((speech+1e-10)/(floor+1e-10)))
 active=float(np.mean(frame_rms>max(.002,speech*.11)))
 return {"seconds":round(len(y)/sr,2),"peak_db":round(20*np.log10(max(peak,1e-9)),2),
   "rms_db":round(20*np.log10(max(rms,1e-9)),2),"clip_fraction":round(float(np.mean(np.abs(y)>.985)),4),
   "quiet_rms_db":round(20*np.log10(max(floor,1e-9)),2),"active_window_fraction":round(active,3),
   "active_to_quiet_db":round(noise_rel_db,1)}
for p in sorted(v.glob("*.wav")):
 y,sr=__import__("soundfile").read(p,dtype="float32")
 if y.ndim>1:y=y.mean(axis=1)
 out={"file":p.name,"all":describe(y,sr)}
 for target in [12,22]:
  if len(y)<sr*target:continue
  top=[]
  for k in range(0,len(y)-sr*target+1,int(sr*.5)):
   z=y[k:k+sr*target]
   x=describe(z,sr)
   score=x["active_window_fraction"]-8*x["clip_fraction"] - max(0,x["quiet_rms_db"]+42)*.001
   top.append((score,k/sr,x))
  _,offset,m=max(top,key=lambda o:o[0])
  out[str(target)+"s_best"]={"offset":round(offset,2),**m}
 print(json.dumps(out,ensure_ascii=True),flush=True)
