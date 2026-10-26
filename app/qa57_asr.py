"""QA57 ASR A/B. The same text windows are used across versions.
Whisper-small on singing is a weak proxy; no claim of exact phonetic correctness.
"""
import os,json,re,subprocess
from pathlib import Path
import numpy as np
R=Path.home()/"Music Studio";D=R/"Diagnostics"/"QA57"
sources={
 "original_ACE":D/"QA57_clean_source_vocals.wav",
 "new_QA57":D/"QA57_phrased_vocal_test.wav",
 "old_QA54":R/"Diagnostics"/"QA54"/"QA54_CFG090_35s.dry.wav",
}
assert all(p.is_file() for p in sources.values())
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
def tokens(x):return re.findall(r"[а-яё]+",x.lower().replace("ё","е"))
def dist(a,b):
 prev=list(range(len(b)+1))
 for i,aa in enumerate(a,1):
  row=[i]
  for j,bb in enumerate(b,1):row.append(min(row[-1]+1,prev[j]+1,prev[j-1]+int(aa!=bb)))
  prev=row
 return prev[-1]
asr={}
for name,path in sources.items():
 chunks=[]
 windows=[(0,16),(16,15),(31,14)] if name!="old_QA54" else [(0,16),(16,15)]
 for start,length in windows:
  out=subprocess.run(["ffmpeg","-nostdin","-v","error","-ss",str(start),"-i",str(path),
     "-t",str(length),"-ac","1","-ar","16000","-f","f32le","pipe:1"],
    capture_output=True,check=True,timeout=70).stdout
  arr=np.frombuffer(out,dtype="<f4").copy()
  features=proc(arr,sampling_rate=16000,return_tensors="pt",return_attention_mask=True)
  with torch.inference_mode():
   output=model.generate(**features,task="transcribe",language="ru",do_sample=False,num_beams=1,max_new_tokens=160)
  s=proc.batch_decode(output,skip_special_tokens=True)[0]
  chunks.append({"begin_s":start,"duration_s":length,"transcript":s,"word_count":len(tokens(s))})
  print("QA57_ASR",name,start,json.dumps(s,ensure_ascii=True),flush=True)
 asr[name]=chunks
deltas=[]
for name in ("new_QA57","old_QA54"):
 total_a=total_edits=0
 for source_row,other_row in zip(asr["original_ACE"],asr[name]):
  a,b=tokens(source_row["transcript"]),tokens(other_row["transcript"])
  e=dist(a,b)
  total_a+=len(a);total_edits+=e
  deltas.append({"version":name,"start_s":source_row["begin_s"],
    "src_words":len(a),"other_words":len(b),"edit_distance":e,"edit_fraction":round(e/max(1,len(a)),3)})
 print("QA57_COMPARE",name,"word_edit_fraction",round(total_edits/max(1,total_a),3),flush=True)
(D/"qa57_asr_comparison.json").write_text(json.dumps({"asr":asr,"metrics":deltas,
 "warning":"Whisper lyrics on singing are often misrecognized, and phoneme jitters are not measured by word edit distance.",
 "independent_human_listening":False},ensure_ascii=False,indent=2),encoding="utf-8")
