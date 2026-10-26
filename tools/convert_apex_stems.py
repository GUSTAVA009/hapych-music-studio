"""HAPYCH optional ApexSVC vocal-only conversion and stereo music remix.

Requires owner-authorized reference voice WAVs and upstream ApexSVC installed
from third_party_versions.json with the compatibility patch. Does not alter
any source WAV or add an unconverted singer layer.
"""
import argparse,json,os,sys,subprocess,hashlib
from pathlib import Path
from math import gcd
os.environ.setdefault("HF_HUB_DISABLE_XET","1")
import numpy as np,soundfile as sf,torch
from scipy.signal import resample_poly

def main():
 parser=argparse.ArgumentParser()
 parser.add_argument("--vocals",type=Path,required=True)
 parser.add_argument("--instrumental",type=Path,required=True)
 parser.add_argument("--reference",type=Path,action="append",required=True)
 parser.add_argument("--output",type=Path,required=True)
 parser.add_argument("--preset",type=Path,required=True)
 parser.add_argument("--apex",type=Path,required=True)
 parser.add_argument("--device",choices=("cpu","cuda"),default="cpu")
 args=parser.parse_args()
 sources=[args.vocals,args.instrumental,*args.reference]
 if any(not x.is_file() for x in sources):raise RuntimeError("Missing source/voice/instrumental file")
 if args.output.exists():raise RuntimeError("Output already exists, refuse overwrite")
 if any(x.resolve()==args.output.resolve() for x in sources):
  raise RuntimeError("Refuse to overwrite an input")
 if len(args.reference)>3:raise ValueError("Maximum three owner-authorized reference recordings")
 p=json.loads(args.preset.read_text(encoding="utf-8"))["parameters"]
 for key in ("topk","alpha","protect","rms_mix_rate","f0_method","f0_filter_radius"):
  if key not in p:raise ValueError(f"Missing preset parameter: {key}")
 src_info=sf.info(args.vocals);inst_info=sf.info(args.instrumental)
 if abs(src_info.duration-inst_info.duration)>.07:raise RuntimeError("Separated stems have different lengths")
 if inst_info.channels!=2:raise RuntimeError("Instrumental must be stereo")
 sys.path.insert(0,str(args.apex))
 os.chdir(args.apex)
 from svc.pipeline import SVCPipeline,ConversionConfig
 opts=dict(p)
 opts["pitch_shift_semitones"]=0
 opts["autotune_strength"]=0
 opts["device"]=args.device
 opts["target_loudness_db"]=None
 cfg=ConversionConfig(**opts)
 pipe=SVCPipeline(checkpoint_dir=args.apex/"checkpoints",device=args.device)
 with torch.inference_mode():
  y,sr=pipe.convert(args.vocals,args.reference,cfg=cfg)
 y=np.asarray(y,dtype="float32").ravel()
 if sr!=24000 or not np.isfinite(y).all():raise RuntimeError("Invalid converted vocal")
 if abs(len(y)/sr-src_info.duration)>.15:raise RuntimeError("Voice converter changed song duration")
 target_sr=inst_info.samplerate
 factor=gcd(sr,target_sr)
 vocal_new=resample_poly(y,target_sr//factor,sr//factor).astype("float32")
 backing,s=sf.read(args.instrumental,always_2d=True,dtype="float32")
 src_v,vr=sf.read(args.vocals,always_2d=True,dtype="float32")
 if not (s==vr==target_sr):raise RuntimeError("Stem sample rates disagree")
 n=len(backing)
 if abs(len(vocal_new)-n)>.15*target_sr:raise RuntimeError("Vocal length mismatch")
 if len(vocal_new)<n:vocal_new=np.pad(vocal_new,(0,n-len(vocal_new)))
 else:vocal_new=vocal_new[:n]
 original=src_v.mean(axis=1)
 if len(original)<n:original=np.pad(original,(0,n-len(original)))
 else:original=original[:n]
 hop=max(1,round(target_sr*.02))
 count=n//hop
 a=np.sqrt(np.mean(original[:count*hop].reshape(count,hop).astype("float64")**2,axis=1)+1e-10)
 b=np.sqrt(np.mean(vocal_new[:count*hop].reshape(count,hop).astype("float64")**2,axis=1)+1e-10)
 active=(a>max(.007,float(np.quantile(a,.78))*.24)) & (b>.002)
 if active.sum()<50:raise RuntimeError("Not enough vocal frames for loudness matching")
 gain=float(np.clip(np.median(a[active]/b[active]),10**(-7/20),10**(7/20)))
 mix=backing.astype("float64")+np.repeat((vocal_new*gain)[:,None],2,axis=1)
 peak=float(np.max(abs(mix)))
 master_gain=min(1.,.945/max(peak,1e-9))
 mix=(mix*master_gain).astype("float32")
 args.output.parent.mkdir(parents=True,exist_ok=True)
 sf.write(args.output,mix,target_sr,subtype="PCM_24")
 mp3=args.output.with_suffix(".mp3")
 if mp3.exists():raise RuntimeError(f"MP3 output already exists: {mp3}")
 proc=subprocess.run(["ffmpeg","-nostdin","-v","error","-y","-i",str(args.output),
  "-c:a","libmp3lame","-b:a","320k",str(mp3)],capture_output=True,text=True,timeout=100)
 if proc.returncode:raise RuntimeError(proc.stderr[-700:])
 qc={"wav":str(args.output),"mp3":str(mp3),"seconds":len(mix)/target_sr,
  "preset":args.preset.name,"pitch_shift_semitones":0,
  "no_original_lead_overdub":True,"dry_vocal_model":"ApexSVC zero-shot",
  "master_peak_dbfs":round(20*np.log10(max(np.max(abs(mix)),1e-9)),2),
  "original_files_unmodified":True,"human_diction_verified":False,
  "wave_sha256":hashlib.sha256(args.output.read_bytes()).hexdigest()}
 args.output.with_suffix(".quality.json").write_text(
  json.dumps(qc,ensure_ascii=False,indent=2),encoding="utf-8")
 print("SAVED_WAV",args.output)
 print("SAVED_MP3",mp3)
if __name__=="__main__":main()
