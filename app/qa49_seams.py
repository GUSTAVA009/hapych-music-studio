from pathlib import Path
import json,numpy as np,soundfile as sf
from scipy.signal import savgol_filter
R=Path.home()/"Music Studio";D=R/"Diagnostics"/"QA45"
p=D/"QA48_MyVoice_Softer_35s.dry.wav"
x,sr=sf.read(p,always_2d=True,dtype="float64")
q=json.loads((D/"QA48_MyVoice_Softer_35s.quality.json").read_text(encoding="utf-8"))
print("frames",q["stitching"]["chunk_starts_frames"],"sr",sr)
for frame in q["stitching"]["chunk_starts_frames"][1:]:
 t=frame/100
 i=int(t*sr)
 if i>=len(x):continue
 for width in (.002,.01,.04):
  z=x[max(0,i-int(width*sr)):min(len(x),i+int(width*sr)),0]
  print("boundary",round(t,2),"span",width,"loud",round(20*np.log10(max(1e-8,np.sqrt(np.mean(z*z)))),1),
    "peakd",round(float(np.max(np.abs(np.diff(z)))),4))
