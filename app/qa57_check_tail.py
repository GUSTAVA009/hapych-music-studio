from pathlib import Path
import numpy as np,soundfile as sf
r=Path.home()/"Music Studio"/"Diagnostics"/"QA54"
for n in ["QA54_CFG090_35s.source.wav","QA54_CFG090_35s.dry.wav"]:
 x,sr=sf.read(r/n,always_2d=True,dtype="float32")
 v=x.mean(axis=1)
 print(n,len(v)/sr,flush=True)
 for t in np.arange(32.0,35,0.25):
  a=int(t*sr);b=int((t+.25)*sr)
  y=v[a:b]
  if not len(y):continue
  print(round(t,2),"rms",round(float(np.sqrt(np.mean(y*y)+1e-10)),4),"peak",round(float(abs(y).max()),3),flush=True)
