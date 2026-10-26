from pathlib import Path
import json,numpy as np,soundfile as sf
R=Path.home()/"Music Studio";D=R/"Diagnostics"/"QA45"
q=json.loads((D/"QA48_MyVoice_Softer_35s.quality.json").read_text(encoding="utf-8"))
print("CHUNKS",q["stitching"])
print("DIPS",q["voice_check"]["metrics"])
for label,name in [("source","QA48_MyVoice_Softer_35s.source.wav"),("dry","QA48_MyVoice_Softer_35s.dry.wav"),("finished","QA48_MyVoice_Softer_35s.finished.wav")]:
 a,sr=sf.read(D/name,always_2d=True)
 a=a.mean(axis=1)
 print(label,"duration",len(a)/sr)
 for start in range(0,35,2):
  z=a[int(start*sr):int((start+2)*sr)]
  rms=20*np.log10(max(1e-7,np.sqrt(np.mean(z*z))))
  print(start,round(rms,1),end="; ")
 print()
