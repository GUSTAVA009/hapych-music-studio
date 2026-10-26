"""QA133: CPU-only zero-shot conversion to owner's real voice references.
Experimental, noncommercial LUNAI source. No voice training, no overdubs,
no chunk slicing, no pitch shift, no studio production modification.
"""
from pathlib import Path
import os
os.environ.update(CUDA_VISIBLE_DEVICES="-1",HF_HUB_OFFLINE="1",
 TRANSFORMERS_OFFLINE="1",TOKENIZERS_PARALLELISM="false",
 OMP_NUM_THREADS="3",MKL_NUM_THREADS="3",OPENBLAS_NUM_THREADS="3")
import sys,json,hashlib,time,traceback,subprocess
import torch,numpy as np,soundfile as sf
sys.stdout.reconfigure(encoding="utf8")
torch.set_num_threads(3)
assert not torch.cuda.is_available(),"GPU unexpectedly exposed"
R=Path.home()/"Music Studio"
D=R/"Integrations"/"OpenUtau-QA129"/"QA132-KogdaPronunciation"/"QA133-FinalDiction"
source_report=json.loads((D/"QA133_render_report.json").read_text(encoding="utf8"))
asr=json.loads((D/"QA133_asr_comparison.json").read_text(encoding="utf8"))
src=Path(source_report["cases"]["A_native_dosht"]["wav"])
assert src.is_file() and hashlib.sha256(src.read_bytes()).hexdigest()==source_report["cases"]["A_native_dosht"]["sha256"]
assert all(x["wer"]==0 for x in asr["cases"]["A_native_dosht"]["lines"])
refs=[
 R/"Мой голос"/"20261022_234327_Микрофон_3867cb.wav",
 R/"Мой голос"/"20261022_183309_Микрофон_df413d.wav"]
ref_hash=[
 "4486fc6a306446c139ace134672ea9ad7054b72ed8da681d03dcce1ae1498d1f",
 "f5751ba2ae6a648a164660ad43e48be4b0eb1261772245e5f5696ca333dd9ba4"]
for p,h in zip(refs,ref_hash):
 assert p.is_file() and hashlib.sha256(p.read_bytes()).hexdigest()==h
import requests
sess=requests.Session();sess.trust_env=False
health=sess.get("http://127.0.0.1:7870/api/health",timeout=8).json()
queue=sess.get("http://127.0.0.1:7862/gradio_api/queue/status",timeout=8).json()
assert health["ready"] and health["job"]["status"] not in ("generating","preparing","converting")
assert queue.get("queue_size",0)==0
assert not any(health.get(key,{}).get("active") for key in ("training23","training32","training41"))
A=R/"Voice Engine"/"alternatives"/"ApexSVC"
sys.path.insert(0,str(A))
os.chdir(A)
from svc.pipeline import SVCPipeline,ConversionConfig
out=D/"QA134-OwnerVoice"
out.mkdir(exist_ok=True)
report={
 "status":"starting","source":str(src),"source_sha256":hashlib.sha256(src.read_bytes()).hexdigest(),
 "source_diction_4_of_4_lines_whisper_exact":True,
 "real_owner_reference_files":[p.name for p in refs],
 "reference_sha256":ref_hash,
 "source_license":"Keiro Revenant LUNAI Project, noncommercial isolated testing only",
 "model":"ApexSVC zero-shot pretrained, CPU only","device":"cpu",
 "training_performed":False,"owner_voice_originals_unchanged":True,
 "other_singer_overlay":False,"pitch_shift_semitones":0,
 "output_human_voice_verified":False,"production_studio_modified":False,
 "candidates":{}}
manifest=out/"QA134_owner_transfer.json"
def save():manifest.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf8")
save()
try:
 print("QA134_OWNER_CPU_LOADING_MODELS",flush=True)
 t0=time.monotonic()
 pipe=SVCPipeline(checkpoint_dir=A/"checkpoints",device="cpu")
 report["model_load_seconds"]=round(time.monotonic()-t0,2)
 report["status"]="model_loaded";save()
 cases=[("max_consonant",{"topk":4,"alpha":.22,"protect":1.0,"rms_mix_rate":.92})]
 for name,params in cases:
  print("QA134_OWNER_CONVERT_BEGIN",name,flush=True)
  start=time.monotonic()
  cfg=ConversionConfig(pitch_shift_semitones=0.0,vad_trim_reference=True,
   f0_method="fcpe",f0_filter_radius=3,autotune_strength=0.0,
   target_loudness_db=None,device="cpu",**params)
  try:
   with torch.inference_mode():
    y,sr=pipe.convert(src,refs,cfg=cfg)
   y=np.asarray(y,dtype="float32").ravel()
   assert sr==24000,(name,sr)
   assert abs(len(y)/sr-20.88)<.06,(name,len(y)/sr)
   assert np.isfinite(y).all()
   pk=float(np.max(np.abs(y)))
   if pk>.985:y=y*.98/pk
   wav=out/("QA134_MyVoice_"+name+"_21s.wav")
   mp3=wav.with_suffix(".mp3")
   sf.write(wav,y,sr,subtype="PCM_24")
   proc=subprocess.run(["ffmpeg","-nostdin","-v","error","-y",
    "-i",str(wav),"-c:a","libmp3lame","-b:a","192k",str(mp3)],
    capture_output=True,text=True,timeout=50)
   assert proc.returncode==0,proc.stderr
   report["candidates"][name]={
    "status":"rendered_pending_quality","wav":str(wav),"mp3":str(mp3),
    "parameters":params,"duration":round(len(y)/sr,3),
    "rms":round(float(np.sqrt(np.mean(y.astype("float64")**2))),6),
    "peak":round(float(np.max(abs(y))),6),
    "sha256":hashlib.sha256(wav.read_bytes()).hexdigest(),
    "conversion_seconds":round(time.monotonic()-start,2)}
   print("QA134_OWNER_WAVE_RENDERED",name,report["candidates"][name]["conversion_seconds"],flush=True)
  except Exception as e:
   report["candidates"][name]={"status":"failed","error":repr(e),"traceback":traceback.format_exc()[-900:]}
   print("QA134_OWNER_WAVE_FAILED",name,repr(e),flush=True)
  save()
 report["status"]="rendered_pending_QA" if any(x["status"]=="rendered_pending_quality" for x in report["candidates"].values()) else "all_failed"
except Exception as e:
 report["status"]="fatal";report["error"]=repr(e)
 report["traceback"]=traceback.format_exc()[-1900:]
 print("QA134_OWNER_FATAL",repr(e),flush=True)
finally:save()
print("QA134_OWNER_SUMMARY",json.dumps({k:v["status"] for k,v in report["candidates"].items()},ensure_ascii=False),flush=True)
