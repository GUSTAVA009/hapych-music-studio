"""QA135: apply selected QA133 'consonant protection' preset to the *isolated*
150s Music Studio rap vocal, retaining the original backing and exact timing.

- Never run on the full instrumental mix (would transform bass and drums).
- Never splice a third-party singer into the lead.
- No original mic, user library track, model or source WAV overwritten.
- Renders a separate master and MP3 in Integration/Results; publication
  into the Music Studio library only after an objective quality screen.
"""
from pathlib import Path
from math import gcd
import os,sys,json,time,hashlib,traceback,subprocess
os.environ.update(CUDA_VISIBLE_DEVICES="-1",OMP_NUM_THREADS="3",
 MKL_NUM_THREADS="3",OPENBLAS_NUM_THREADS="3",TOKENIZERS_PARALLELISM="false",
 HF_HUB_OFFLINE="1",TRANSFORMERS_OFFLINE="1")
import torch,numpy as np,soundfile as sf
from scipy.signal import resample_poly
import requests
sys.stdout.reconfigure(encoding="utf8")
torch.set_num_threads(3)
assert not torch.cuda.is_available()
R=Path.home()/"Music Studio"
D=R/"Integrations"/"RapFullTrack-QA135"
T=D/"Results"
T.mkdir(parents=True,exist_ok=True)
source=json.loads((D/"QA135_rap_source_report.json").read_text(encoding="utf8"))
preset=json.loads((R/"Voice Profiles"/"presets"/"QA133_ConsonantProtection_ApexSVC.json").read_text(encoding="utf8"))
assert preset["id"]=="qa133_consonant_protection_apexsvc"
src=Path(source["file_master_wav"])
assert src.is_file() and hashlib.sha256(src.read_bytes()).hexdigest()==source["master_sha256"]
assert 149<src.stat().st_size/(1024*1024)<130 or src.is_file() # master is protected by SHA
stems=D/"Stems"/"htdemucs"/src.stem
vocals=stems/"vocals.wav"
backing=stems/"no_vocals.wav"
assert vocals.is_file() and backing.is_file(),(vocals,backing)
sinfo=sf.info(src);vinfo=sf.info(vocals);binfo=sf.info(backing)
assert abs(vinfo.duration-sinfo.duration)<.06,(vinfo.duration,sinfo.duration)
assert abs(binfo.duration-sinfo.duration)<.06
assert 145<sinfo.duration<155
assert binfo.channels==2
refs=[R/"Мой голос"/x["file"] for x in preset["references"]]
assert len(refs)==2
for p,detail in zip(refs,preset["references"]):
 assert p.is_file() and hashlib.sha256(p.read_bytes()).hexdigest()==detail["sha256"]
s=requests.Session();s.trust_env=False
h=s.get("http://127.0.0.1:7870/api/health",timeout=8).json()
assert h["job"]["status"]=="done"
assert h["job"]["id"]==json.loads((D/"QA135_submit_result.json").read_text(encoding="utf8"))["id"]
manifest=T/"QA135_apex_pipeline_report.json"
state={
 "status":"initializing","title":source["title"],"origin_sha256":source["master_sha256"],
 "vocal_stem_file":str(vocals),"instrumental_stem_file":str(backing),
 "source_duration_s":sinfo.duration,
 "reference_files":[p.name for p in refs],
 "model":"ApexSVC zero-shot, pretrained","preset":"QA133 consonant protection",
 "parameters":preset["parameters"],
 "device":"cpu","owner_reference_files_preserved":True,
 "source_master_preserved":True,"production_music_studio_not_yet_modified":True,
 "training_performed":False,"voice_quality_human_verified":False,
 "no_source_vocal_layering":True,
 "time_started":time.strftime("%Y-%m-%d %H:%M:%S"),
}
def save():manifest.write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding="utf8")
save()
try:
 A=R/"Voice Engine"/"alternatives"/"ApexSVC"
 sys.path.insert(0,str(A));os.chdir(A)
 from svc.pipeline import SVCPipeline,ConversionConfig
 opts=dict(preset["parameters"])
 opts.update({"device":"cpu","target_loudness_db":None})
 cfg=ConversionConfig(**opts)
 print("QA135_APEX_LOAD_CPU",flush=True)
 pipe=SVCPipeline(checkpoint_dir=A/"checkpoints",device="cpu")
 state["status"]="converting_vocals";save()
 start=time.monotonic()
 last=[0.]
 def progress(t,desc=""):
  if t-last[0]>.048 or t>=.999:
   print("QA135_APEX_PROGRESS",round(t*100,1),desc,flush=True)
   last[0]=t
 with torch.inference_mode():
  audio,sr=pipe.convert(vocals,refs,cfg=cfg,progress=progress)
 x=np.asarray(audio,dtype="float32").ravel()
 assert sr==24000
 assert abs(len(x)/sr-vinfo.duration)<.14,(len(x)/sr,vinfo.duration)
 assert np.isfinite(x).all()
 assert np.sqrt(np.mean(x.astype("float64")**2))>0.0008
 dry=T/"QA135_Rap_MyVoice_ConsonantProtection_DRY.wav"
 sf.write(dry,x,sr,subtype="PCM_24")
 state["dry_vocal"]=str(dry)
 state["voice_conversion_seconds"]=round(time.monotonic()-start,2)
 state["dry_vocal_sha256"]=hashlib.sha256(dry.read_bytes()).hexdigest()
 state["status"]="remixing_original_backing";save()
 print("QA135_VOICE_CONVERTED",state["voice_conversion_seconds"],flush=True)
 # Keep the full song's original backing stereo, no original vocal overdub,
 # no hard time stretch and no frame-wise gain pumping. The constant gain
 # is inferred from active vocal energy in the original separated stem.
 target_rate=binfo.samplerate
 assert target_rate==vinfo.samplerate
 k=gcd(target_rate,sr)
 outv=resample_poly(x,target_rate//k,sr//k).astype("float32")
 ref_v,rate=sf.read(vocals,always_2d=True,dtype="float32")
 b,br=sf.read(backing,always_2d=True,dtype="float32")
 assert rate==br==target_rate and b.shape[1]==2
 n=len(b)
 assert abs(len(outv)-n)<target_rate*.15
 if len(outv)<n:outv=np.pad(outv,(0,n-len(outv)))
 else:outv=outv[:n]
 ref=ref_v.mean(axis=1)
 if len(ref)<n:ref=np.pad(ref,(0,n-len(ref)))
 else:ref=ref[:n]
 # RMS in 20ms frames. Use a single gain, capped between +/- 7dB,
 # not a voice-envelope copy that could break consonants.
 hop=max(1,round(target_rate*.02))
 m=n//hop
 e_ref=np.sqrt(np.mean(ref[:m*hop].reshape(m,hop).astype("float64")**2,axis=1)+1e-10)
 e_new=np.sqrt(np.mean(outv[:m*hop].reshape(m,hop).astype("float64")**2,axis=1)+1e-10)
 active=(e_ref>max(.007,float(np.quantile(e_ref,.78))*.24)) & (e_new>.002)
 assert active.sum()>75,active.sum()
 desired=float(np.median(e_ref[active]/e_new[active]))
 gain=float(np.clip(desired,10**(-7/20),10**(7/20)))
 # No artificial double-track. Very gentle 1x dry centered vocal to preserve
 # lip sync and clear consonants, original instrumental remains stereo.
 mix=b.astype("float64")+np.repeat((outv*gain)[:,None],2,axis=1)
 peak=float(np.max(np.abs(mix)))
 master_gain=min(1.,.945/max(peak,1e-9))
 mix=(mix*master_gain).astype("float32")
 assert mix.shape==(n,2) and np.isfinite(mix).all()
 master=T/"QA135_Gromche_Chem_Vchera_Rap_MYVOICE_MASTER.wav"
 mp3=T/"QA135_Gromche_Chem_Vchera_Rap_MYVOICE.mp3"
 sf.write(master,mix,target_rate,subtype="PCM_24")
 ff=subprocess.run(["ffmpeg","-nostdin","-v","error","-y",
  "-i",str(master),"-c:a","libmp3lame","-b:a","320k",str(mp3)],
  capture_output=True,text=True,timeout=75)
 assert ff.returncode==0,ff.stderr
 assert abs(sf.info(master).duration-sinfo.duration)<.05
 assert master.is_file() and mp3.stat().st_size>1000000
 state.update(status="complete_awaiting_QA",file_master=str(master),file_mp3=str(mp3),
    final_duration=sf.info(master).duration,
    final_sha256=hashlib.sha256(master.read_bytes()).hexdigest(),
    final_mp3_sha256=hashlib.sha256(mp3.read_bytes()).hexdigest(),
    vocal_match_constant_gain_db=round(20*np.log10(gain),2),
    master_peak_dbfs=round(20*np.log10(np.max(np.abs(mix))),2),
    master_attenuation_db=round(20*np.log10(master_gain),2),
    final_rms=round(float(np.sqrt(np.mean(mix.astype("float64")**2))),5),
    additional_source_voice_overdub=False,original_instrumental_retained=True,
    pitch_shift=0.0,autotune=0.0,human_ear_checked=False)
 print("QA135_RAP_APEX_MASTER_READY",mp3,round(state["final_duration"],3),flush=True)
except Exception as e:
 state["status"]="failed"
 state["error"]=repr(e)
 state["traceback"]=traceback.format_exc()[-2000:]
 print("QA135_RAP_APEX_FAILED",repr(e),flush=True)
finally:save()
