"""QA58 old vs raw-F0 identical-source word check (Whisper-small, imperfect on singing)."""
import os,re,json,subprocess
from pathlib import Path
import numpy as np
R=Path.home()/"Music Studio";D=R/"Diagnostics"/"QA58";Q=R/"Diagnostics"/"QA54"
new=list((D/"synth").glob("vc_*.wav"));assert len(new)==1
files={"source_original":Q/"QA54_CFG090_35s.source.wav",
 "cleanF0_QA54":Q/"QA54_CFG090_35s.dry.wav",
 "rawF0_QA58":new[0]}
os.environ.update(HF_HUB_OFFLINE="1",TRANSFORMERS_OFFLINE="1",HF_HUB_DISABLE_TELEMETRY="1")
import torch
from transformers import AutoProcessor,WhisperForConditionalGeneration,GenerationConfig
torch.set_num_threads(3)
assets=R/"Diagnostics"/"rejected-light-audit"/"whisper_text_assets"
cache=R/"Voice Engine"/"seed-vc"/"checkpoints"/"hf_cache"/"models--openai--whisper-small"/"snapshots"/"973afd24965f72e36ca33b3055d56a652f456b4d"
proc=AutoProcessor.from_pretrained(str(assets),local_files_only=True)
model=WhisperForConditionalGeneration.from_pretrained(str(cache),local_files_only=True,torch_dtype=torch.float32).eval()
model.generation_config=GenerationConfig.from_pretrained(str(assets),local_files_only=True)
model.generation_config.forced_decoder_ids=None;model.config.forced_decoder_ids=None
def toks(s):return re.findall(r"[а-яё]+",s.lower().replace("ё","е"))
def lev(a,b):
 prev=list(range(len(b)+1))
 for i,x in enumerate(a,1):
  row=[i]
  for j,y in enumerate(b,1):row.append(min(row[-1]+1,prev[j]+1,prev[j-1]+int(x!=y)))
  prev=row
 return prev[-1]
transcripts={}
for label,path in files.items():
 rows=[]
 for begin,duration in [(0,16),(16,15)]:
  raw=subprocess.run(["ffmpeg","-nostdin","-v","error","-ss",str(begin),"-i",str(path),
     "-t",str(duration),"-ac","1","-ar","16000","-f","f32le","pipe:1"],capture_output=True,check=True,timeout=50).stdout
  features=proc(np.frombuffer(raw,dtype="<f4").copy(),sampling_rate=16000,return_tensors="pt",return_attention_mask=True)
  with torch.inference_mode():
   ids=model.generate(**features,task="transcribe",language="ru",do_sample=False,num_beams=1,max_new_tokens=150)
  txt=proc.batch_decode(ids,skip_special_tokens=True)[0]
  rows.append({"begin_s":begin,"text":txt})
  print("QA58_ASR",label,begin,json.dumps(txt,ensure_ascii=True),flush=True)
 transcripts[label]=rows
vals=[]
for label in ("cleanF0_QA54","rawF0_QA58"):
 e=n=0
 for ref,cand in zip(transcripts["source_original"],transcripts[label]):
  a=toks(ref["text"]);b=toks(cand["text"])
  e+=lev(a,b);n+=len(a)
 vals.append({"variant":label,"relative_edits":round(e/max(1,n),3),"errors":e,"source_words":n})
(D/"qa58_asr_report.json").write_text(json.dumps({"transcripts":transcripts,"metrics":vals,
 "warning":"ASR does not detect all discontinuities; manual listening required."},ensure_ascii=False,indent=2),encoding="utf-8")
print("QA58_WORD_COMPARE",json.dumps(vals,ensure_ascii=True),flush=True)
