"""QA44 held-out recording generalization check, base vs fine-tuned
using same unseen 12s microphone reference. ASR is imperfect.
"""
from pathlib import Path
import os,json,subprocess,re
import numpy as np
ROOT=Path.home()/"Music Studio";D=ROOT/"Diagnostics"/"QA44"
prior=json.loads((D/"qa44_ab_comparison.json").read_text(encoding="utf-8"))
source=prior["asr_samples"]["source"]
files=[("holdout_baseline",D/"QA44_base_holdout_40s"),("holdout_finetuned",D/"QA44_tuned_holdout_40s")]
assert all(f.with_suffix(".dry.wav").is_file() and f.with_suffix(".quality.json").is_file() for _,f in files)
os.environ.update(HF_HUB_OFFLINE="1",TRANSFORMERS_OFFLINE="1",HF_HUB_DISABLE_TELEMETRY="1")
import torch
from transformers import AutoProcessor,WhisperForConditionalGeneration,GenerationConfig
torch.set_num_threads(3)
assets=ROOT/"Diagnostics"/"rejected-light-audit"/"whisper_text_assets"
cache=ROOT/"Voice Engine"/"seed-vc"/"checkpoints"/"hf_cache"/"models--openai--whisper-small"/"snapshots"/"973afd24965f72e36ca33b3055d56a652f456b4d"
processor=AutoProcessor.from_pretrained(str(assets),local_files_only=True)
model=WhisperForConditionalGeneration.from_pretrained(str(cache),local_files_only=True,torch_dtype=torch.float32).eval()
model.generation_config=GenerationConfig.from_pretrained(str(assets),local_files_only=True)
model.generation_config.forced_decoder_ids=None;model.config.forced_decoder_ids=None
def tokens(v):return re.findall(r"[а-яё]+",v.casefold().replace("ё","е"))
def lev(a,b):
 prev=list(range(len(b)+1))
 for i,x in enumerate(a,1):
  curr=[i]
  for j,y in enumerate(b,1):curr.append(min(curr[-1]+1,prev[j]+1,prev[j-1]+int(x!=y)))
  prev=curr
 return prev[-1]
result=[]
for name,path in files:
 transcripts=[];errors=0;source_count=0
 for index,offset in enumerate((0,18)):
  b=subprocess.run(["ffmpeg","-nostdin","-v","error","-ss",str(offset),
      "-i",str(path.with_suffix(".dry.wav")),"-t","22","-ac","1","-ar","16000",
      "-f","f32le","pipe:1"],capture_output=True,check=True,timeout=120).stdout
  y=np.frombuffer(b,dtype="<f4").copy()
  inputs=processor(y,sampling_rate=16000,return_tensors="pt",return_attention_mask=True)
  with torch.inference_mode():
   ids=model.generate(**inputs,task="transcribe",language="ru",do_sample=False,num_beams=1,max_new_tokens=170)
  phrase=processor.batch_decode(ids,skip_special_tokens=True)[0]
  a,c=tokens(source[index]["text"]),tokens(phrase)
  count=lev(a,c)
  transcripts.append({"start_seconds":offset,"reference_text":source[index]["text"],
                      "converted_text":phrase,"source_words":len(a),"converted_words":len(c),"edit_distance":count})
  errors+=count;source_count+=len(a)
  print("QA44_HOLDOUT_ASR",name,offset,json.dumps(phrase,ensure_ascii=True)[:750],flush=True)
 q=json.loads(path.with_suffix(".quality.json").read_text(encoding="utf-8"))
 item={"name":name,"unseen_reference":True,
       "relative_source_asr_error":round(errors/max(1,source_count),3),
       "speaker_cosine_proxy":q.get("speaker_embedding_cosine"),
       "weak_vocal_frames":q.get("voice_check",{}).get("metrics",{}).get("relative_missing_vocal_frames"),
       "dropouts":q.get("voice_check",{}).get("metrics",{}).get("energy_dip_events"),
       "pitch_status":q.get("pitch_consistency",{}).get("status"),
       "transcripts":transcripts}
 result.append(item)
 print("QA44_HOLDOUT_METRICS",json.dumps({k:v for k,v in item.items() if k!="transcripts"},ensure_ascii=True),flush=True)
(D/"qa44_holdout_asr_report.json").write_text(json.dumps({"variants":result,"human_identity_verified":False,
  "speech_recognition_imperfect":True,"reference_kept_out_of_finetuning":True},ensure_ascii=False,indent=2),encoding="utf-8")
