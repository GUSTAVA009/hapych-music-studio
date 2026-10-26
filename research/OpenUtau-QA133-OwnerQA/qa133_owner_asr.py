"""QA133 lexical QA of two freshly converted owner timbre tracks.
Local-only Whisper-small. Note that automatic recognizer is not an
ear-based guarantee about accent, individual phonemes or owner likeness.
"""
from pathlib import Path
import os,sys,json,re,hashlib
from math import gcd
os.environ.update(HF_HUB_OFFLINE="1",TRANSFORMERS_OFFLINE="1",TOKENIZERS_PARALLELISM="false")
import numpy as np,torch,soundfile as sf
from scipy.signal import resample_poly
from transformers import AutoProcessor,WhisperForConditionalGeneration,GenerationConfig
sys.stdout.reconfigure(encoding="utf8")
torch.set_num_threads(3)
R=Path.home()/"Music Studio"
O=R/"Integrations"/"OpenUtau-QA129"
D=O/"QA132-KogdaPronunciation"/"QA133-FinalDiction"/"QA133-OwnerVoice"
manifest=json.loads((D/"QA133_owner_transfer.json").read_text(encoding="utf8"))
assert manifest["status"]=="rendered_pending_QA"
assert len(manifest["candidates"])==2
sidecar=json.loads((O/"QA129_Score"/"QA129_phones.json").read_text(encoding="utf8"))
assets=R/"Diagnostics"/"rejected-light-audit"/"whisper_text_assets"
weights=R/"Voice Engine"/"seed-vc"/"checkpoints"/"hf_cache"/"models--openai--whisper-small"/"snapshots"/"973afd24965f72e36ca33b3055d56a652f456b4d"
p=AutoProcessor.from_pretrained(str(assets),local_files_only=True)
m=WhisperForConditionalGeneration.from_pretrained(str(weights),local_files_only=True,torch_dtype=torch.float32).eval()
m.generation_config=GenerationConfig.from_pretrained(str(assets),local_files_only=True)
m.generation_config.forced_decoder_ids=None;m.config.forced_decoder_ids=None
def to16(path):
 y,sr=sf.read(path,dtype="float32",always_2d=True)
 y=y.mean(axis=1)
 if sr!=16000:
  g=gcd(sr,16000);y=resample_poly(y,16000//g,sr//g).astype("float32")
 return y
def trans(y):
 inp=p(y,sampling_rate=16000,return_tensors="pt",return_attention_mask=True)
 with torch.inference_mode():
  seq=m.generate(**inp,language="ru",task="transcribe",do_sample=False,num_beams=1,max_new_tokens=100)
 return p.batch_decode(seq,skip_special_tokens=True)[0].strip()
def words(t):return re.findall(r"[а-яё]+",t.lower().replace("ё","е"))
def ed(exp,hyp):
 x=words(exp);z=words(hyp);row=list(range(len(z)+1))
 for token in x:
  next_row=[row[0]+1]
  for i,w in enumerate(z):next_row.append(min(next_row[-1]+1,row[i+1]+1,row[i]+(token!=w)))
  row=next_row
 return row[-1]
expected=["Мне нужен свет твоих окон.","Меня услышишь и поймёшь.",
 "Когда за окном идёт дождь.","Сохрани мою любовь."]
results={"status":"evaluated_by_ASR_not_human","model":"whisper-small","cases":{}}
for name,item in manifest["candidates"].items():
 assert item["status"]=="rendered_pending_quality"
 wav=Path(item["wav"])
 assert hashlib.sha256(wav.read_bytes()).hexdigest()==item["sha256"]
 y=to16(wav)
 assert abs(len(y)/16000-20.88)<.05
 lines=[]
 for i,ref in enumerate(expected,1):
  group=[x for x in sidecar["syllables"] if x["line"]==i]
  start=group[0]["tick"]*60/(102*480)
  end=(group[-1]["tick"]+group[-1]["duration_ticks"])*60/(102*480)+.4
  txt=trans(y[round(start*16000):round(end*16000)])
  wer=round(ed(ref,txt)/len(words(ref)),3)
  lines.append({"line":i,"expected":ref,"transcribed":txt,"WER":wer})
  print("QA133_OWNER_ASR",name,i,"WER",wer,"WORDS",txt,flush=True)
 full=trans(y)
 full_wer=round(ed(" ".join(expected),full)/sum(len(words(e)) for e in expected),3)
 results["cases"][name]={"lines":lines,"full":full,"full_WER":full_wer,
   "all_lines_lexically_exact":all(x["WER"]==0 for x in lines),
   "full_lexical_exact":full_wer==0}
 (D/"QA133_owner_asr_report.json").write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding="utf8")
 print("QA133_OWNER_ASR_SUMMARY",name,full_wer,
       "LINES_OK",sum(x["WER"]==0 for x in lines),flush=True)
print("QA133_OWNER_ASR_COMPLETE",flush=True)
