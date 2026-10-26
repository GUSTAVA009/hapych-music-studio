from pathlib import Path
import soundfile as sf, numpy as np, json
from scipy.signal import find_peaks
r=Path.home()/"Music Studio"/"Diagnostics"/"QA45"
paths={"source":r/"QA45_MyVoice_QA44_35s.source.wav","dry45":r/"QA45_MyVoice_QA44_35s.dry.wav","dry48":r/"QA48_MyVoice_Softer_35s.dry.wav","finished48":r/"QA48_MyVoice_Softer_35s.finished.wav"}
for name,p in paths.items():
 y,sr=sf.read(p,dtype="float32",always_2d=True);y=y.mean(axis=1)
 win=int(sr*.05)
 energies=np.array([np.sqrt(np.mean(z*z)) for z in np.array_split(y[:len(y)//win*win],len(y)//win)])
 print(name,"duration",round(len(y)/sr,2),"db_windows",[(round(i*.05,2),round(20*np.log10(max(float(energies[i]),1e-8)),1)) for i in np.argsort(energies)[-5:]],flush=True)
 for a,b in [(0,6),(6,10),(10,16),(16,22),(22,30),(30,35)]:
  x=energies[int(a/.05):int(b/.05)]
  db=20*np.log10(np.maximum(x,1e-8))
  local=np.abs(np.diff(db))
  print("REGION",name,a,b,"rms_med",round(float(np.median(db)),1),"fast_jump_gt5dB",int((local>5).sum()),"max_jump",round(float(local.max()),1),flush=True)
q=json.loads((r/"QA48_MyVoice_Softer_35s.quality.json").read_text(encoding="utf-8"))
print("CHUNKS",q["stitching"],flush=True)
