"""QA130 investigate ASR sensitivity to four line boundaries without audio edits."""
from pathlib import Path
from math import gcd
import os,json,re,sys
os.environ.update(HF_HUB_OFFLINE="1",TRANSFORMERS_OFFLINE="1",TOKENIZERS_PARALLELISM="false")
import numpy as np,soundfile as sf,torch
from scipy.signal import resample_poly
from transformers import AutoProcessor,WhisperForConditionalGeneration,GenerationConfig
sys.stdout.reconfigure(encoding="utf-8")
torch.set_num_threads(4)
R=Path.home()/"Music Studio"
D=R/"Integrations"/"RussianOrthoepy"/"QA130-OwnerTimbre"
S=R/"Voice Engine"/"seed-vc"
assets=R/"Diagnostics"/"rejected-light-audit"/"whisper_text_assets"
weights=S/"checkpoints"/"hf_cache"/"models--openai--whisper-small"/"snapshots"/"973afd24965f72e36ca33b3055d56a652f456b4d"
proc=AutoProcessor.from_pretrained(str(assets),local_files_only=True)
m=WhisperForConditionalGeneration.from_pretrained(str(weights),local_files_only=True,torch_dtype=torch.float32).eval()
m.generation_config=GenerationConfig.from_pretrained(str(assets),local_files_only=True)
m.generation_config.forced_decoder_ids=None;m.config.forced_decoder_ids=None
paths={
 "source":R/"Integrations"/"OpenUtau-QA129"/"QA129_Score"/"QA129_Keiro_Russian_RealSinging_21s.wav",
 "A":D/"QA130_MyVoice_consonant_safe_21s.wav",
 "B":D/"QA130_MyVoice_identity_focused_21s.wav"}
def transcribe(audio,rate,start,end):
 chunk=audio[round(start*rate):round(end*rate)]
 if rate!=16000:
  g=gcd(rate,16000)
  chunk=resample_poly(chunk,16000//g,rate//g).astype("float32")
 inputs=proc(chunk,sampling_rate=16000,return_tensors="pt",return_attention_mask=True)
 with torch.inference_mode():
  ids=m.generate(**inputs,language="ru",task="transcribe",do_sample=False,num_beams=1,max_new_tokens=100)
 return proc.batch_decode(ids,skip_special_tokens=True)[0]
out={"source_unchanged":True,"model":"Whisper-small","verified_by_ear":False,"tested_windows":[]}
for tag,path in paths.items():
 audio,rate=sf.read(path,dtype="float32",always_2d=True)
 mono=audio.mean(axis=1)
 for start,end in ((14.9,20.88),(15.3,20.88),(15.735,20.88)):
  t=transcribe(mono,rate,start,end)
  line={"candidate":tag,"start_sec":start,"end_sec":end,"text":t}
  out["tested_windows"].append(line)
  print("QA130_LAST_PHRASE_WINDOW",json.dumps(line,ensure_ascii=False),flush=True)
(D/"QA130_boundary_asr.json").write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding="utf-8")
