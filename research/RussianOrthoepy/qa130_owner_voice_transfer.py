"""QA130: private, isolated voice-conversion inference on a test-only LUNAI
render, with the user's two real owned microphone takes.
No third-party audio/model trains or fine-tunes anything; no model edits.
No re-overlay, no splicing, no transposition, no production integration.
Acoustic sample is for non-commercial phonetic/timbre evaluation only.
"""
from pathlib import Path
import sys,os,hashlib,json,time,traceback
os.environ.update(HF_HUB_OFFLINE="1",TRANSFORMERS_OFFLINE="1",TOKENIZERS_PARALLELISM="false")
import numpy as np,soundfile as sf,torch
ROOT=Path.home()/"Music Studio"
D=ROOT/"Integrations"/"RussianOrthoepy"/"QA130-OwnerTimbre"
D.mkdir(parents=True,exist_ok=True)
SOURCE=ROOT/"Integrations"/"OpenUtau-QA129"/"QA129_Score"/"QA129_Keiro_Russian_RealSinging_21s.wav"
MANIFEST=ROOT/"Integrations"/"OpenUtau-QA129"/"QA129_Score"/"QA129_real_singing_report.json"
A=ROOT/"Voice Engine"/"alternatives"/"ApexSVC"
REFS=[
 ROOT/"Мой голос"/"20261022_234327_Микрофон_3867cb.wav",
 ROOT/"Мой голос"/"20261022_183309_Микрофон_df413d.wav"]
EXPECTED={
 "20261022_234327_Микрофон_3867cb.wav":"4486fc6a306446c139ace134672ea9ad7054b72ed8da681d03dcce1ae1498d1f",
 "20261022_183309_Микрофон_df413d.wav":"f5751ba2ae6a648a164660ad43e48be4b0eb1261772245e5f5696ca333dd9ba4"}
manifest=json.loads(MANIFEST.read_text(encoding="utf-8"))
assert manifest["status"]=="four_sung_fragments_merged"
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==manifest["wav_sha256"]
for p in REFS:
 assert p.is_file()
 assert hashlib.sha256(p.read_bytes()).hexdigest()==EXPECTED[p.name]
assert 20.7<sf.info(SOURCE).duration<21.1
import requests
sess=requests.Session();sess.trust_env=False
health=sess.get("http://127.0.0.1:7870/api/health",timeout=8).json()
queue=sess.get("http://127.0.0.1:7862/gradio_api/queue/status",timeout=8).json()
busy=health["job"]["status"] in ("generating","preparing","converting")
busy=busy or any(health.get(k,{}).get("active") for k in ("training23","training32","training41"))
busy=busy or queue.get("queue_size",0)>0
if busy:raise RuntimeError("MUSIC_STUDIO_BUSY, no parallel GPU conversion")
assert torch.cuda.is_available()
gpu=torch.cuda.get_device_name(0)
torch.set_num_threads(4)
os.chdir(A);sys.path.insert(0,str(A))
from svc.pipeline import SVCPipeline,ConversionConfig
report={"version":"QA130","status":"starting","source_file":SOURCE.name,
 "source_sha256":manifest["wav_sha256"],"reference_files":[p.name for p in REFS],
 "speaker_profile_mode":"existing user-owned real microphones, 23s and 31s",
 "source_license":"Keiro Revenant from LUNAI Project; noncommercial QA only, no model port or training",
 "sound_engine":"ApexSVC zero-shot pretrained model, inference only",
 "GPU":gpu,"project_production_unchanged":True,"voice_records_unchanged":True,
 "other_singer_spliced":False,"voice_overlay":False,"pitch_shift_semitones":0,
 "autotune":0,"model_weights_modified":False,"third_party_audio_used_for_training":False,
 "original_singers_voice_not_intentionally_overlaid":True,"human_owner_identity_verified":False,
 "human_pronunciation_verified":False,"candidates":{}}
output=D/"qa130_transfer_report.json"
def save():output.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
save()
try:
 pipe=SVCPipeline(checkpoint_dir=A/"checkpoints",device="cuda")
 report["status"]="model_loaded";save()
 cases=[("consonant_safe",{"topk":6,"alpha":0.35,"protect":0.82,"rms_mix_rate":0.95}),
        ("identity_focused",{"topk":4,"alpha":0.22,"protect":0.58,"rms_mix_rate":0.92})]
 for tag,kwargs in cases:
  now=time.monotonic()
  print("QA130_BEGIN",tag,flush=True)
  cfg=ConversionConfig(
    pitch_shift_semitones=0.0,vad_trim_reference=True,
    f0_method="fcpe",f0_filter_radius=3,
    autotune_strength=0.0,target_loudness_db=None,**kwargs)
  try:
   with torch.inference_mode():audio,sr=pipe.convert(SOURCE,REFS,cfg=cfg)
   x=np.asarray(audio,dtype="float32").ravel()
   assert sr==24000 and abs(len(x)/sr-sf.info(SOURCE).duration)<0.055
   assert np.isfinite(x).all()
   peak=float(np.max(np.abs(x)))
   if peak>.995:x=x*.985/peak
   dst=D/("QA130_MyVoice_"+tag+"_21s.wav")
   sf.write(dst,x,sr,subtype="PCM_24")
   mp3=D/("QA130_MyVoice_"+tag+"_21s.mp3")
   import subprocess
   proc=subprocess.run(["ffmpeg","-nostdin","-v","error","-y",
      "-i",str(dst),"-c:a","libmp3lame","-b:a","192k",str(mp3)],
      capture_output=True,text=True,timeout=35)
   assert proc.returncode==0,proc.stderr
   row={"status":"rendered","filepath":str(dst),"mp3_path":str(mp3),
     "params":kwargs,"duration":round(len(x)/sr,3),
     "rms":round(float(np.sqrt(np.mean(x.astype("float64")**2))),5),
     "peak":round(float(np.max(np.abs(x))),5),
     "sha256":hashlib.sha256(dst.read_bytes()).hexdigest(),
     "generation_seconds":round(time.monotonic()-now,2),
     "phonemes_verified":False,"owner_timbre_verified":False}
   print("QA130_RENDER_DONE",tag,row["generation_seconds"],"SECONDS",flush=True)
  except Exception as e:
   row={"status":"failed","error":repr(e),"detail":traceback.format_exc()[-1000:]}
   print("QA130_RENDER_FAILED",tag,repr(e),flush=True)
  report["candidates"][tag]=row
  save()
  torch.cuda.empty_cache()
 report["status"]="rendered_pending_QA" if any(c["status"]=="rendered" for c in report["candidates"].values()) else "failed"
except Exception as e:
 report["status"]="failed"
 report["fatal_error"]=repr(e)
 report["traceback"]=traceback.format_exc()[-1700:]
 print("QA130_FATAL",repr(e),flush=True)
finally:save()
print("QA130_SUMMARY",json.dumps({"status":report["status"],"cases":{k:v["status"] for k,v in report["candidates"].items()}},ensure_ascii=False),flush=True)
