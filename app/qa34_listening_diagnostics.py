from pathlib import Path
import importlib.util, json, numpy as np, soundfile as sf
R=Path.home()/"Music Studio";directory=R/"Мои треки"
path=next(iter(sorted(directory.glob("*QA34*.mp3"),key=lambda p:p.stat().st_mtime,reverse=True)))
master=R/"Мастер WAV"/(path.stem+".wav")
print("MODULES",{x:bool(importlib.util.find_spec(x)) for x in ("faster_whisper","whisper","librosa","torch","transformers","soundfile","scipy")},flush=True)
print("MASTER",master.exists(),"MB",round(master.stat().st_size/1e6,2) if master.exists() else None)
source=master if master.exists() else path
a,sr=sf.read(str(source),dtype="float32",always_2d=True)
print("AUDIO_SR",sr,"DURATION",round(len(a)/sr,3),"CHANNELS",a.shape[1],flush=True)
def rms_db(x):
 return round(float(20*np.log10(max(1e-12,np.sqrt(np.mean(np.asarray(x,dtype=np.float64)**2))))),2)
stats=[]
for i in range(0,len(a),int(sr*5)):
 p=a[i:min(i+int(sr*5),len(a))]
 if len(p)<sr/5:continue
 mid=(p[:,0]+p[:,1])*.5;side=(p[:,0]-p[:,1])*.5
 cor=np.corrcoef(p.T)[0,1] if p.shape[1]==2 else 1.
 stats.append({"start":round(i/sr,1),"rms_dbfs":rms_db(p),"side_vs_mid_db":round(rms_db(side)-rms_db(mid),2),"corr":round(float(cor),3)})
print("STEREO_SEGMENTS",json.dumps(stats,ensure_ascii=False),flush=True)
print("PEAK_DBFS",round(20*np.log10(max(1e-9,np.max(np.abs(a)))),2))
for path in [Path.home()/".cache"/"huggingface"/"hub",R/"Voice Engine"/"models",R/"ACE-Step-1.5"/"models"]:
 if path.exists():
  folders=[x.name for x in path.iterdir() if x.is_dir()]
  print("MODEL_DIR",str(path),"DIRS",folders[:30],flush=True)
