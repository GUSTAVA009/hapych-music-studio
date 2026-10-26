"""QA44 held-out singing source speech test: base vs clean-mic pilot.
Whisper-small is an imperfect proxy; do not treat ASR as final listener QA.
"""
import os,json,re,subprocess,time
from pathlib import Path
import numpy as np
ROOT=Path.home()/"Music Studio";D=ROOT/"Diagnostics"/"QA44"
base=ROOT/"Diagnostics"/"QA43"/"QA43_MyVoice_AltRef_22s_40steps.dry.wav"
fresh=D/"QA44_Finetuned_40s_MyVoice_22sec.dry.wav"
source=ROOT/"Diagnostics"/"QA43"/"QA43_MyVoice_22s_40steps.source.wav"
paths={"source":source,"base_qa43":base,"fine_tuned_qa44":fresh}
assert all(f.is_file() for f in paths.values()),paths
os.environ.update(HF_HUB_OFFLINE="1",TRANSFORMERS_OFFLINE="1",HF_HUB_DISABLE_TELEMETRY="1")
import torch
from transformers import AutoProcessor,WhisperForConditionalGeneration,GenerationConfig
torch.set_num_threads(3)
assets=ROOT/"Diagnostics"/"rejected-light-audit"/"whisper_text_assets"
cache=ROOT/"Voice Engine"/"seed-vc"/"checkpoints"/"hf_cache"/"models--openai--whisper-small"/"snapshots"/"973afd24965f72e36ca33b3055d56a652f456b4d"
proc=AutoProcessor.from_pretrained(str(assets),local_files_only=True)
model=WhisperForConditionalGeneration.from_pretrained(str(cache),local_files_only=True,torch_dtype=torch.float32).eval()
model.generation_config=GenerationConfig.from_pretrained(str(assets),local_files_only=True)
model.generation_config.forced_decoder_ids=None;model.config.forced_decoder_ids=None
def tokens(s):return re.findall(r"[а-яё]+",s.casefold().replace("ё","е"))
def levenshtein(a,b):
 prev=list(range(len(b)+1))
 for i,x in enumerate(a,1):
  row=[i]
  for j,y in enumerate(b,1):row.append(min(row[-1]+1,prev[j]+1,prev[j-1]+int(x!=y)))
  prev=row
 return prev[-1]
asr={}
for name,file in paths.items():
 parts=[]
 for offset in (0,18):
  b=subprocess.run(["ffmpeg","-nostdin","-v","error","-ss",str(offset),"-i",str(file),"-t","22",
        "-ar","16000","-ac","1","-f","f32le","pipe:1"],capture_output=True,check=True,timeout=90).stdout
  y=np.frombuffer(b,dtype="<f4").copy()
  features=proc(y,sampling_rate=16000,return_tensors="pt",return_attention_mask=True)
  with torch.inference_mode():
   ids=model.generate(**features,task="transcribe",language="ru",do_sample=False,num_beams=1,max_new_tokens=160)
  txt=proc.batch_decode(ids,skip_special_tokens=True)[0]
  parts.append({"start_s":offset,"text":txt,"words":len(tokens(txt))})
  print("QA44_ASR",name,offset,json.dumps(txt,ensure_ascii=True)[:600],flush=True)
 asr[name]=parts
results=[]
for name,folder,stem in [
 ("base_qa43",ROOT/"Diagnostics"/"QA43","QA43_MyVoice_AltRef_22s_40steps"),
 ("fine_tuned_qa44",D,"QA44_Finetuned_40s_MyVoice_22sec")
]:
 v=json.loads((folder/(stem+".quality.json")).read_text(encoding="utf-8"))
 diffs=[];source_tokens=0
 for a,b in zip(asr["source"],asr[name]):
  x,y=tokens(a["text"]),tokens(b["text"])
  n=levenshtein(x,y);source_tokens+=len(x)
  diffs.append({"start_s":a["start_s"],"source_tokens":len(x),"transferred_tokens":len(y),"edits":n})
 item={"name":name,
    "relative_asr_word_edit":round(sum(x["edits"] for x in diffs)/max(1,source_tokens),3),
    "source_tokens":source_tokens,
    "speaker_cosine_proxy":v.get("speaker_embedding_cosine"),
    "missed_vocal_fraction":v.get("voice_check",{}).get("metrics",{}).get("relative_missing_vocal_frames"),
    "dropout_events":v.get("voice_check",{}).get("metrics",{}).get("energy_dip_events"),
    "max_dropout_s":v.get("voice_check",{}).get("metrics",{}).get("longest_energy_dip_s"),
    "pitch_consistency":v.get("pitch_consistency",{}).get("status"),
    "accepted_by_voice_guard":v.get("voice_check",{}).get("accepted"),
    "word_differences":diffs}
 results.append(item)
 print("QA44_COMPARE",json.dumps({k:v for k,v in item.items() if k!="word_differences"},ensure_ascii=True),flush=True)
data={"testing":"Original QA42 source unchanged; controlled baseline and fine-tuned matched conditions",
 "results":results,"asr_samples":asr,
 "speaker_similarity_not_verified_by_owner":True,
 "diction_not_verified_by_listener":True,
 "no_model_deployment":True}
(D/"qa44_ab_comparison.json").write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8")
print("QA44_QA_COMPLETE",flush=True)
