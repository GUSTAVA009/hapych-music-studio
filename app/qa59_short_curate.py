"""QA59 articulation curriculum: 20 clean short phrases from existing 10 long,
no new speaker, no synthetic augmentation, no overlap, holdout still untouched.
"""
from pathlib import Path
import json,hashlib,numpy as np,soundfile as sf
from scipy.ndimage import gaussian_filter1d
R=Path.home()/"Music Studio";D=R/"Diagnostics"/"QA59"
long=D/"curated_44k";short=D/"articulation_44k";short.mkdir(parents=True,exist_ok=True)
manifest=json.loads((D/"qa59_dataset_manifest.json").read_text(encoding="utf-8"))
assert len(manifest["segments"])==10
parts=[]
for r in manifest["segments"]:
 p=long/r["file"];wave,sr=sf.read(p,dtype="float32",always_2d=True)
 assert sr==44100 and wave.shape[1]==1
 y=wave[:,0];hop=round(.02*sr);count=len(y)//hop
 rms=np.sqrt(np.mean(y[:count*hop].reshape(count,hop).astype(float)**2,axis=1)+1e-12)
 sm=gaussian_filter1d(rms,sigma=3)
 center=len(y)//(2*hop);a=max(round(1.8/.02),center-43);b=min(count-round(1.8/.02),center+43)
 assert b>a+3,(p,len(y)/sr,a,b)
 position=(a+int(np.argmin(sm[a:b])))*hop
 assert position/sr>1.8 and (len(y)-position)/sr>1.8
 for i,(start,end) in enumerate(((0,position),(position,len(y))),1):
  x=y[start:end].copy()
  edge=int(sr*.015)
  if start>0:x[:edge]*=np.sin(np.linspace(0,np.pi/2,edge))**2
  if end<len(y):x[-edge:]*=np.cos(np.linspace(0,np.pi/2,edge))**2
  out=short/(p.stem+f"_short{i}.wav")
  sf.write(out,x,sr,subtype="FLOAT")
  record={"name":out.name,"source":r["source_file"],"from_long":r["file"],
          "duration_s":round(len(x)/sr,3),
          "sha256":hashlib.sha256(out.read_bytes()).hexdigest()}
  parts.append(record)
  print("QA59_SHORT",json.dumps(record,ensure_ascii=True),flush=True)
assert len(parts)==20
assert len(list(short.glob("*.wav")))==20
assert abs(sum(s["duration_s"] for s in parts)-manifest["training_audio_real_seconds"])<.05
report={"role":"stage2 short-phrase articulation curriculum",
 "segments":parts,"real_data_seconds":manifest["training_audio_real_seconds"],
 "new_training_speakers":0,"augmentation":False,"only_train_source_audio":True,
 "nonoverlap_in_originals":True,"holdout_never_used":True}
(D/"qa59_short_manifest.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
print("QA59_SHORT_CURRICULUM_READY",len(parts),round(sum(s["duration_s"] for s in parts),2),flush=True)
