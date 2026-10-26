from pathlib import Path
import json,importlib.util,hashlib,soundfile as sf,numpy as np
R=Path.home()/"Music Studio"
libs={m:importlib.util.find_spec(m) is not None for m in ['pyworld','parselmouth','pysptk','scipy','librosa','torch','torchaudio','numpy','soundfile','speechbrain']}
print('LIBRARIES',json.dumps(libs))
files=list((R/"Мой голос").glob("*.wav"))+list((R/"Diagnostics"/"QA57").glob("reference_selected.wav"))
train=json.loads((R/"Diagnostics"/"QA59"/"qa59_dataset_manifest.json").read_text(encoding="utf-8"))
known={m["source_sha256"]:m["role"] for m in train["sources"]}
for p in files:
 try:
  audio,sr=sf.read(p,dtype="float32",always_2d=True)
  x=audio.mean(axis=1); rms=np.sqrt(np.mean(x*x)+1e-12)
  print('VOICE_FILE',json.dumps({"name":p.name,"sec":round(len(x)/sr,2),"sr":sr,"nch":audio.shape[1],"rms_db":round(float(20*np.log10(rms)),2),"peak":round(float(np.max(abs(x))),3),"train_role":known.get(hashlib.sha256(p.read_bytes()).hexdigest(),"not in prior user dataset")},ensure_ascii=True))
 except Exception as e:print('VOICE_ERR',p.name,str(e))
