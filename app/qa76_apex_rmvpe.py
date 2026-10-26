"""QA76 ApexSVC: retain exact source melody using RMVPE F0 from original ACE,
not FCPE heuristic. No autotune, no pitch shift. Reuse 54s user mic reference.
Two isolated settings, CPU/GPU compatible and no production side effects.
"""
from pathlib import Path
import sys,os,json,time,hashlib
import numpy as np,soundfile as sf
from scipy.signal import resample_poly
R=Path.home()/"Music Studio";D=R/"Diagnostics"/"QA76";D.mkdir(parents=True,exist_ok=True)
A=R/"Voice Engine"/"alternatives"/"ApexSVC";sys.path.insert(0,str(A))
os.chdir(A);os.environ["HF_HUB_OFFLINE"]="1";os.environ["TRANSFORMERS_OFFLINE"]="1"
os.environ["HF_HUB_DISABLE_TELEMETRY"]="1"
from svc.pipeline import SVCPipeline,ConversionConfig
import svc.pipeline as module
f0file=D/"qa76_source_f0_rmvpe.npy"
f0=np.load(f0file,allow_pickle=False).astype(np.float64)
assert 3490<len(f0)<3515
src=R/"Diagnostics"/"QA54"/"QA54_CFG090_35s.source.wav"
refs=[]
for code in ("3867cb","df413d"):
 found=list((R/"Мой голос").glob("*"+code+".wav"))
 assert len(found)==1,found
 refs.append(found[0])
oldcompute=module.compute_f0
def original_melody(filename,*args,**kwargs):
 if Path(filename).resolve()==src.resolve():
  return f0.copy()
 return oldcompute(filename,*args,**kwargs)
module.compute_f0=original_melody
s=SVCPipeline(checkpoint_dir=A/"checkpoints",device="cuda")
# Treat current QA54 master as fixed backing for meaningful A/B.
sys.path.insert(0,str(R/"Voice Engine"))
from studio_mix21 import vocal_room
from studio_mix20 import power_frames
from studio_mix16 import db
q=R/"Diagnostics"/"QA54"
baseline=json.loads((q/"QA54_CFG090_35s.quality.json").read_text(encoding="utf-8"))
master,sr=sf.read(baseline["master"],dtype="float32",always_2d=True)
old,ss=sf.read(q/"QA54_CFG090_35s.finished.wav",dtype="float32",always_2d=True)
source_audio,original_sr=sf.read(src,dtype="float32",always_2d=True)
assert ss==sr==original_sr==44100
n=len(master);master_gain=10**(float(baseline["mix"]["master_gain_db"])/20)
def fit(a):
 y=a.mean(axis=1)
 return np.pad(y,(0,max(0,n-len(y))))[:n]
source_44=fit(source_audio);old_44=fit(old)
music=master/master_gain-vocal_room(old_44,sr)
assert np.sqrt(np.mean(((music+vocal_room(old_44,sr))*master_gain-master)**2))<1e-5
variants=[
 {"name":"RMVPE_K4_P55","topk":4,"alpha":.08,"protect":.55,"rms":.2},
 {"name":"RMVPE_K4_P80","topk":4,"alpha":.18,"protect":.80,"rms":.25},
]
results=[]
for v in variants:
 cfg=ConversionConfig(topk=v["topk"],alpha=v["alpha"],protect=v["protect"],
  rms_mix_rate=v["rms"],pitch_shift_semitones=0,
  f0_filter_radius=3,autotune_strength=0.0,
  vad_trim_reference=False,device="cuda",
  checkpoint_dir=A/"checkpoints")
 t=time.monotonic()
 print("QA76_RUNNING",v["name"],flush=True)
 with __import__("torch").inference_mode():
  result,rate=s.convert(src,refs,cfg=cfg)
 assert rate==24000
 if abs(len(result)/rate-n/sr)>.15:raise RuntimeError("Source song length changed")
 dry24=D/(v["name"]+"_24k.wav")
 sf.write(dry24,result,rate,subtype="FLOAT")
 audio=resample_poly(result,147,80).astype(np.float32)
 audio=np.pad(audio,(0,max(0,n-len(audio))))[:n]
 assert np.isfinite(audio).all()
 dry=D/(v["name"]+"_44k_dry.wav")
 sf.write(dry,audio,sr,subtype="FLOAT")
 ratio1=power_frames(source_44,sr//100);ratio2=power_frames(audio,sr//100)
 active=(ratio1>max(10**(-48/20),float(np.percentile(ratio1,85))*.15))&(ratio2>10**(-55/20))
 assert active.sum()>150
 leveldb=float(np.clip(np.median(db(ratio1[active])-db(ratio2[active])),-16,16))
 mixed=(music+vocal_room(audio*10**(leveldb/20),sr))*master_gain
 peak=float(np.max(abs(mixed)))
 mixed*=min(1.0,.89/max(peak,1e-8))
 wav=D/(v["name"]+"_Master24.wav")
 mp3=D/(v["name"]+"_35s_320kbps.mp3")
 sf.write(wav,mixed,sr,subtype="PCM_24")
 import subprocess
 proc=subprocess.run(["ffmpeg","-nostdin","-v","error","-y","-i",str(wav),
 "-c:a","libmp3lame","-b:a","320k",str(mp3)],capture_output=True,text=True,timeout=90)
 assert proc.returncode==0,proc.stderr[-800:]
 meta={"name":v["name"],"source_pitch_exact_RMVPE_100hz":True,
   "frames":len(f0),"no_auto_pitch":True,"pitch_shift_semitones":0,
   "topk":v["topk"],"alpha":v["alpha"],"protect":v["protect"],
   "ref_user_only":True,"no_new_train":True,"not_deployed":True,
   "elapsed_s":round(time.monotonic()-t,2),"raw":str(dry),
   "master":str(wav),"mp3":str(mp3),"bytes":mp3.stat().st_size,
   "sha256":hashlib.sha256(mp3.read_bytes()).hexdigest()}
 results.append(meta)
 (D/"qa76_benchmark.json").write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding="utf-8")
 print("QA76_SAMPLE_READY",json.dumps(meta,ensure_ascii=True),flush=True)
print("QA76_ALL_FINISHED",flush=True)
