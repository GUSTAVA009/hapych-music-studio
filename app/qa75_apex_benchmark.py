"""QA75 isolated ApexSVC zero-shot singing benchmark using two authorized user
microphone references. SOURCE: the same ACE-step 35s lead as QA54/QA67.
Fixed pitch_shift=0 semitones. No auto vocal pitch, no retraining, no current
app/models modified. All outputs stay in Diagnostics/QA75.
"""
from pathlib import Path
import sys,os,subprocess,json,time,hashlib,requests
import numpy as np,soundfile as sf
from scipy.signal import resample_poly
R=Path.home()/"Music Studio";D=R/"Diagnostics"/"QA75";D.mkdir(parents=True,exist_ok=True)
V=R/"Voice Engine";A=V/"alternatives"/"ApexSVC"
sys.path.insert(0,str(V))
Q=R/"Diagnostics"/"QA54"
py=A/".venv"/"Scripts"/"python.exe"
assert py.is_file()
source=Q/"QA54_CFG090_35s.source.wav"
refs=[]
for code in ("3867cb","df413d"):
 found=list((R/"Мой голос").glob("*"+code+".wav"))
 assert len(found)==1,(code,found)
 refs.append(found[0])
assert source.is_file()
weightpaths=[A/"checkpoints"/"WavLM-Large.pt",A/"checkpoints"/"G_150k.pt"]
assert all(p.is_file() and p.stat().st_size>20*1024*1024 for p in weightpaths),weightpaths
h=requests.Session();h.trust_env=False
health=h.get("http://127.0.0.1:7870/api/health",timeout=6).json()
if health["job"]["status"] in ("preparing","generating","converting"):
 raise RuntimeError("Existing Music Studio generation active. Avoid parallel RTX4060 use.")
from studio_mix21 import vocal_room
b=json.loads((Q/"QA54_CFG090_35s.quality.json").read_text(encoding="utf-8"))
master,sr=sf.read(b["master"],dtype="float32",always_2d=True)
qa54,old_sr=sf.read(Q/"QA54_CFG090_35s.finished.wav",dtype="float32",always_2d=True)
src,ss=sf.read(source,dtype="float32",always_2d=True)
assert sr==ss==old_sr==44100
n=len(master);gain=10**(float(b["mix"]["master_gain_db"])/20)
def fit(x):
 x=x.mean(axis=1)
 return np.pad(x,(0,max(0,n-len(x))))[:n]
old=fit(qa54)
bed=master/gain-vocal_room(old,sr)
assert np.sqrt(np.mean((((bed+vocal_room(old,sr))*gain)-master)**2))<1e-5
configs=[
 {"label":"Apex_K4_Protect40","topk":4,"alpha":.08,"protect":.40,"rms":.20},
 {"label":"Apex_K8_Protect55","topk":8,"alpha":.12,"protect":.55,"rms":.25},
]
results=[]
for c in configs:
 out=D/(c["label"]+"_24k_dry.wav")
 log=D/(c["label"]+"_cli.log")
 assert not out.exists(),"Refuse overwrite of prior test "+str(out)
 cmd=[str(py),"-u","-m","svc.cli","-v","convert","--src",str(source),
 "--ref",str(refs[0]),"--ref",str(refs[1]),"--out",str(out),
 "--topk",str(c["topk"]),"--pitch-shift","0",
 "--alpha",str(c["alpha"]),"--protect",str(c["protect"]),
 "--rms-mix-rate",str(c["rms"]),"--no-vad-trim",
 "--f0-method","fcpe","--f0-filter-radius","3",
 "--autotune-strength","0","--device","cuda"]
 started=time.monotonic()
 print("QA75_START",c["label"],flush=True)
 env=os.environ.copy()
 env.update(PYTHONUTF8="1",PYTHONIOENCODING="utf-8",HF_HUB_OFFLINE="1",
 TRANSFORMERS_OFFLINE="1",HF_HUB_DISABLE_TELEMETRY="1",
 NO_PROXY="127.0.0.1,localhost,::1",no_proxy="127.0.0.1,localhost,::1")
 with log.open("w",encoding="utf-8") as file:
  try:rc=subprocess.run(cmd,cwd=A,stdin=subprocess.DEVNULL,stdout=file,
     stderr=subprocess.STDOUT,timeout=760,env=env).returncode
  except subprocess.TimeoutExpired:rc=124
 result={"version":c["label"],"exit":rc,"seconds":round(time.monotonic()-started,1),
 "source":str(source),"refs":[str(p) for p in refs],
 "shift_semitones":0,"no_autotune":True,"experiment_isolated":True,"production_unchanged":True,
 "checkpoint_sizes":[p.stat().st_size for p in weightpaths],
 "license":"AGPL3 upstream; bench only, not automatically suitable for closed service"}
 if rc==0 and out.is_file():
  a,s=sf.read(out,dtype="float32",always_2d=True)
  assert s==24000 and a.shape[1]==1 and abs(len(a)/s-n/sr)<.15,(s,a.shape,n/sr)
  v=resample_poly(a[:,0],147,80).astype(np.float32)
  v=np.pad(v,(0,max(0,n-len(v))))[:n]
  assert np.isfinite(v).all()
  dry44=D/(c["label"]+"_44k_dry.wav")
  sf.write(dry44,v,sr,subtype="FLOAT")
  # match overall speech level to input ACE without syllabic gain riding
  from studio_mix20 import power_frames
  from studio_mix16 import db
  src_v=fit(src)
  hop=sr//100
  r1=power_frames(src_v,hop);r2=power_frames(v,hop)
  active=(r1>max(10**(-48/20),float(np.percentile(r1,85))*.15))&(r2>10**(-55/20))
  assert active.sum()>100
  delta=float(np.clip(np.median(db(r1[active])-db(r2[active])),-16,16))
  prepared=v*10**(delta/20)
  song=(bed+vocal_room(prepared,sr))*gain
  peak=float(np.max(abs(song)));song*=min(1,.89/max(peak,1e-9))
  wav=D/(c["label"]+"_Master24.wav")
  mp3=D/(c["label"]+"_35s_320kbps.mp3")
  sf.write(wav,song,sr,subtype="PCM_24")
  ff=subprocess.run(["ffmpeg","-nostdin","-v","error","-y","-i",str(wav),
    "-c:a","libmp3lame","-b:a","320k",str(mp3)],capture_output=True,text=True,timeout=100)
  assert ff.returncode==0,ff.stderr[-500:]
  result.update(dry_44k=str(dry44),wav=str(wav),mp3=str(mp3),
      bytes=mp3.stat().st_size,sha256=hashlib.sha256(mp3.read_bytes()).hexdigest(),
      vocal_gain_db=round(delta,2))
 else:
  result["log_tail"]=log.read_text(encoding="utf-8",errors="replace")[-4000:]
 results.append(result)
 (D/"qa75_benchmark.json").write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding="utf-8")
 print("QA75_VARIANT",json.dumps({k:v for k,v in result.items() if k not in ("checkpoint_sha256","log_tail")},ensure_ascii=True),flush=True)
 if rc!=0:
  print("QA75_FAILED",result.get("log_tail"),flush=True)
  sys.exit(rc)
print("QA75_BOTH_COMPLETE",flush=True)
