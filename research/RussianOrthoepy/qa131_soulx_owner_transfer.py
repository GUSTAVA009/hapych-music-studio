"""QA131 isolated SoulX singing voice transfer (noncommercial LUNAI test output).
Inference only. Real owner microphone reference; no model adaptation/training,
no pitch shift, no mixing of two singer waveforms, no Music Studio changes.
"""
from pathlib import Path
import os,sys,json,hashlib,time,traceback,gc,random,subprocess
from math import gcd
os.environ.update(HF_HUB_OFFLINE="1",TRANSFORMERS_OFFLINE="1",TOKENIZERS_PARALLELISM="false",
 HF_HUB_CACHE=str(Path.home()/"Music Studio"/"Experiments"/"SoulX-Singer"/"pretrained_models"/"hf_cache"))
import numpy as np,soundfile as sf,torch
from scipy.signal import resample_poly
R=Path.home()/"Music Studio"
D=R/"Integrations"/"RussianOrthoepy"/"QA131-SoulX"
D.mkdir(parents=True,exist_ok=True)
SOURCE=R/"Integrations"/"OpenUtau-QA129"/"QA129_Score"/"QA129_Keiro_Russian_RealSinging_21s.wav"
REF=R/"Мой голос"/"20261022_234327_Микрофон_3867cb.wav"
M=R/"Integrations"/"OpenUtau-QA129"/"QA129_Score"/"QA129_real_singing_report.json"
assert SOURCE.is_file() and REF.is_file()
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==json.loads(M.read_text(encoding="utf8"))["wav_sha256"]
assert hashlib.sha256(REF.read_bytes()).hexdigest()=="4486fc6a306446c139ace134672ea9ad7054b72ed8da681d03dcce1ae1498d1f"
import requests
s=requests.Session();s.trust_env=False
status=s.get("http://127.0.0.1:7870/api/health",timeout=7).json()
queue=s.get("http://127.0.0.1:7862/gradio_api/queue/status",timeout=7).json()
assert status["job"]["status"] not in ("generating","converting","preparing") and queue.get("queue_size",0)==0
assert not any(status.get(key,{}).get("active") for key in ("training23","training32","training41"))
torch.set_num_threads(3)
assert torch.cuda.is_available()
def prep(name,path):
 samples,sr=sf.read(path,dtype="float32",always_2d=True)
 mono=samples.mean(axis=1)
 def resample(target):
  g=gcd(sr,target)
  return resample_poly(mono,target//g,sr//g).astype("float32")
 wav24=resample(24000)
 sf.write(D/f"{name}.wav",wav24,24000,subtype="PCM_24")
 wav16=resample(16000)
 return wav24,wav16
wav_src24,wav_src16=prep("target",SOURCE)
wav_ref24,wav_ref16=prep("prompt",REF)
assert len(wav_ref24)>24000*29 and abs(len(wav_src24)/24000-20.88)<.06
S=R/"Voice Engine"/"seed-vc"
os.chdir(S);sys.path.insert(0,str(S))
from modules.rmvpe import RMVPE
from hf_utils import load_custom_model_from_hf
est=RMVPE(load_custom_model_from_hf("lj1995/VoiceConversionWebUI","rmvpe.pt",None),is_half=False,device=torch.device("cuda"))
for name,lo,hi in (("target",wav_src16,wav_src24),("prompt",wav_ref16,wav_ref24)):
 hz=np.asarray(est.infer_from_audio(lo,thred=.03),dtype="float32").ravel()
 n=(len(hi)+479)//480
 f50=hz[np.minimum(np.arange(n)*2,len(hz)-1)]
 assert len(f50)>300 and np.isfinite(f50).all()
 np.save(D/f"{name}_f0.npy",f50)
 print("QA131_PREP",name,len(hi)/24000,"F0_MEDIAN",float(np.median(f50[f50>55])),flush=True)
del est;gc.collect();torch.cuda.empty_cache()
SOUL=R/"Experiments"/"SoulX-Singer"
checkpoint=SOUL/"pretrained_models"/"SoulX-Singer"/"model-svc.pt"
assert checkpoint.is_file()
sys.path.insert(0,str(SOUL/"deps"));sys.path.insert(0,str(SOUL))
os.environ["HF_HUB_CACHE"]=str(SOUL/"pretrained_models"/"hf_cache")
os.chdir(SOUL)
from cli.inference_svc import build_model,process
from soulxsinger.utils.file_utils import load_config
from types import SimpleNamespace
report={"status":"starting","scope":"noncommercial pronunciation/voice identity testing only",
 "engine":"SoulX-Singer-SVC zero-shot","model_trained":False,
 "external_training_data_used":False,
 "source":"QA129 Keiro Revenant from LUNAI Project (derived acoustic sample, inference input only)",
 "original_mic":REF.name,"source_pitch_shift":0,"auto_pitch_shift":False,
 "production_modified":False,"originals_unchanged":True,"source_waveform_blending":False}
manifest=D/"qa131_run_report.json"
def save():manifest.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf8")
save()
try:
 random.seed(13126);np.random.seed(13126);torch.manual_seed(13126);torch.cuda.manual_seed_all(13126)
 cfg=load_config("soulxsinger/config/soulxsinger.yaml")
 print("QA131_LOADING_SOULX",flush=True)
 model=build_model(model_path=str(checkpoint),config=cfg,device="cuda",use_fp16=True)
 out=D/"SoulX_Inference"
 out.mkdir(parents=True,exist_ok=True)
 args=SimpleNamespace(device="cuda",model_path=str(checkpoint),config="soulxsinger/config/soulxsinger.yaml",
  prompt_wav_path=str(D/"prompt.wav"),target_wav_path=str(D/"target.wav"),
  prompt_f0_path=str(D/"prompt_f0.npy"),target_f0_path=str(D/"target_f0.npy"),
  save_dir=str(out),auto_shift=False,pitch_shift=0,n_steps=32,cfg=1.5,use_fp16=True)
 t=time.monotonic()
 with torch.inference_mode():process(args,cfg,model)
 original=out/"generated.wav"
 assert original.is_file()
 wav,sr=sf.read(original,dtype="float32",always_2d=True)
 assert abs(len(wav)/sr-20.88)<.08 and np.isfinite(wav).all(),(sr,wav.shape)
 mono=wav.mean(axis=1)
 peak=float(np.max(abs(mono)))
 if peak>=.98:mono=mono*.97/peak
 result=D/"QA131_SoulX_MyVoice_21s.wav"
 sf.write(result,mono,sr,subtype="PCM_24")
 mp3=D/"QA131_SoulX_MyVoice_21s.mp3"
 proc=subprocess.run(["ffmpeg","-nostdin","-v","error","-y","-i",str(result),
  "-c:a","libmp3lame","-b:a","192k",str(mp3)],capture_output=True,text=True,timeout=50)
 assert proc.returncode==0,proc.stderr
 report.update(status="rendered_pending_QA",wav=str(result),mp3=str(mp3),
  duration=round(len(mono)/sr,3),sample_rate=sr,
  sha256=hashlib.sha256(result.read_bytes()).hexdigest(),
  elapsed_seconds=round(time.monotonic()-t,2),
  peak=round(float(np.max(abs(mono))),4))
 print("QA131_SOULX_RENDERED",report["duration"],report["elapsed_seconds"],str(result),flush=True)
except Exception as e:
 report["status"]="failed";report["error"]=repr(e)
 report["traceback"]=traceback.format_exc()[-2000:]
 print("QA131_ERROR",repr(e),flush=True)
finally:save()
