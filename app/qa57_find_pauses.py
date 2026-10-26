from pathlib import Path
import numpy as np,soundfile as sf
R=Path.home()/"Music Studio"
r=R/"Diagnostics"/"QA54"/"QA54_CFG090_35s.source.wav"
y,sr=sf.read(r,always_2d=True,dtype="float32");y=y.mean(axis=1)
hop=int(sr*.02);n=len(y)//hop
rms=np.sqrt(np.mean(y[:n*hop].reshape(n,hop)**2,axis=1)+1e-12)
for sec in [4,6,8,9,11,13,15,17,19,21,23,25,27,29,31,33]:
 center=int(sec/.02); a=max(0,center-35);b=min(n,center+35)
 z=sorted([(round(float(rms[i]),5),round(i*.02,2)) for i in range(a,b) if .02<i*.02<(len(y)/sr-.02)])
 print("WINDOW",sec,"LOW_ENERGY",z[:4],flush=True)
print("SOURCE",len(y)/sr,"RATE",sr,"MAX",float(np.max(np.abs(y))),flush=True)
