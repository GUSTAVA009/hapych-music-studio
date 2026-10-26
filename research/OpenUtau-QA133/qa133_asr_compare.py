"""Test QA133 A/B Russian lyrics by Whisper-small ASR, local-only CPU.
Automatic lexical accuracy is not human proof of stressed vowels or voice.
"""
from pathlib import Path
import json,re,sys,os
from math import gcd
os.environ.update(HF_HUB_OFFLINE="1",TRANSFORMERS_OFFLINE="1",TOKENIZERS_PARALLELISM="false")
import numpy as np,soundfile as sf,torch
from scipy.signal import resample_poly
from transformers import AutoProcessor,WhisperForConditionalGeneration,GenerationConfig
sys.stdout.reconfigure(encoding="utf8")
torch.set_num_threads(2)
R=Path.home()/"Music Studio"
O=R/"Integrations"/"OpenUtau-QA129"
D=O/"QA132-KogdaPronunciation"/"QA133-FinalDiction"
cases=json.loads((D/"QA133_render_report.json").read_text(encoding="utf8"))["cases"]
sidecar=json.loads((O/"QA129_Score"/"QA129_phones.json").read_text(encoding="utf8"))
weights=R/"Voice Engine"/"seed-vc"/"checkpoints"/"hf_cache"/"models--openai--whisper-small"/"snapshots"/"973afd24965f72e36ca33b3055d56a652f456b4d"
assets=R/"Diagnostics"/"rejected-light-audit"/"whisper_text_assets"
proc=AutoProcessor.from_pretrained(str(assets),local_files_only=True)
model=WhisperForConditionalGeneration.from_pretrained(str(weights),local_files_only=True,torch_dtype=torch.float32).eval()
model.generation_config=GenerationConfig.from_pretrained(str(assets),local_files_only=True)
model.generation_config.forced_decoder_ids=None
model.config.forced_decoder_ids=None
def read16(path):
 audio,sr=sf.read(path,always_2d=True,dtype="float32")
 a=audio.mean(axis=1)
 if sr!=16000:
  g=gcd(sr,16000)
  a=resample_poly(a,16000//g,sr//g).astype("float32")
 return a
def trans(y):
 inp=proc(y,sampling_rate=16000,return_tensors="pt",return_attention_mask=True)
 with torch.inference_mode():
  ids=model.generate(**inp,language="ru",task="transcribe",do_sample=False,num_beams=1,max_new_tokens=100)
 return proc.batch_decode(ids,skip_special_tokens=True)[0].strip()
def words(t):return re.findall(r"[а-яё]+",t.lower().replace("ё","е"))
def word_edit(x,y):
 a,b=words(x),words(y)
 row=list(range(len(b)+1))
 for w in a:
  next_row=[row[0]+1]
  for j,t in enumerate(b):
   next_row.append(min(next_row[-1]+1,row[j+1]+1,row[j]+(w!=t)))
  row=next_row
 return row[-1]
expected=["Мне нужен свет твоих окон.","Меня услышишь и поймёшь.",
 "Когда за окном идёт дождь.","Сохрани мою любовь."]
out={"status":"evaluated","asr_model":"local Whisper-small, nonhuman listening",
     "stress_and_naturalness_unverified":True,"cases":{}}
for tag,item in cases.items():
 a=read16(item["wav"])
 assert abs(len(a)/16000-20.88)<.08
 lines=[]
 for line,exp in enumerate(expected,1):
  syllables=[x for x in sidecar["syllables"] if x["line"]==line]
  start=syllables[0]["tick"]*60/(480*102)
  end=(syllables[-1]["tick"]+syllables[-1]["duration_ticks"])*60/(480*102)+.4
  hyp=trans(a[round(start*16000):round(end*16000)])
  n=word_edit(exp,hyp);wer=round(n/len(words(exp)),3)
  lines.append({"line":line,"reference":exp,"recognized":hyp,
                "edit_distance_words":n,"wer":wer})
  print("QA133_ASR",tag,line,"WER",wer,"TEXT",hyp,flush=True)
 full=trans(a)
 m=word_edit(" ".join(expected),full)
 row={"lines":lines,"full_transcript":full,"full_edit":m,
      "full_WER":round(m/sum(len(words(x)) for x in expected),3),
      "line3_contains_rain":("дождь" in words(lines[2]["recognized"])),
      "line4_contains_moyu":("мою" in words(lines[3]["recognized"])),
      "line3_starts_kogda":("когда" in words(lines[2]["recognized"]))}
 out["cases"][tag]=row
 print("QA133_WER_SUMMARY",tag,row["full_WER"],row["line3_contains_rain"],row["line4_contains_moyu"],flush=True)
 (D/"QA133_asr_comparison.json").write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding="utf8")
print("QA133_ASR_COMPLETE",flush=True)
