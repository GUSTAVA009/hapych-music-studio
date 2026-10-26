"""QA40 A/B Russian vocal-preservation audit on isolated dry stems.
The original vocal and two converted outputs use the same source seconds.
Offline Whisper-small; subjective naturalness and voice identity not certified.
"""
from pathlib import Path
import os,json,subprocess,re,difflib
import numpy as np
R=Path.home()/"Music Studio";D=R/"Diagnostics"/"QA40"
paths={
 "source_original_demucs_vocal":D/"QA40_MyVoice_22secRef_40steps.source.wav",
 "candidate_12sec_reference":D/"QA40_MyVoice_12secRef_40steps.dry.wav",
 "candidate_22sec_reference":D/"QA40_MyVoice_22secRef_40steps.dry.wav",
}
assert all(x.is_file() for x in paths.values()),{k:str(p) for k,p in paths.items() if not p.exists()}
os.environ.update(HF_HUB_OFFLINE="1",TRANSFORMERS_OFFLINE="1",HF_HUB_DISABLE_TELEMETRY="1")
import torch
from transformers import AutoProcessor,WhisperForConditionalGeneration,GenerationConfig
torch.set_num_threads(3)
assets=R/"Diagnostics"/"rejected-light-audit"/"whisper_text_assets"
cache=R/"Voice Engine"/"seed-vc"/"checkpoints"/"hf_cache"/"models--openai--whisper-small"/"snapshots"/"973afd24965f72e36ca33b3055d56a652f456b4d"
processor=AutoProcessor.from_pretrained(str(assets),local_files_only=True)
model=WhisperForConditionalGeneration.from_pretrained(str(cache),local_files_only=True,torch_dtype=torch.float32).eval()
model.generation_config=GenerationConfig.from_pretrained(str(assets),local_files_only=True)
model.generation_config.forced_decoder_ids=None;model.config.forced_decoder_ids=None
texts={}
def tokens(t):return re.findall(r"[а-яё]+",t.lower().replace("ё","е"))
for name,p in paths.items():
 chunks=[]
 for start,seconds in [(0,22),(18,22)]:
  cmd=["ffmpeg","-nostdin","-v","error","-ss",str(start),"-i",str(p),"-t",str(seconds),"-ac","1","-ar","16000","-f","f32le","pipe:1"]
  raw=subprocess.run(cmd,capture_output=True,check=True,timeout=90).stdout
  y=np.frombuffer(raw,dtype="<f4").copy()
  if y.size<16000*7:continue
  features=processor(y,sampling_rate=16000,return_tensors="pt",return_attention_mask=True)
  with torch.inference_mode():
   ids=model.generate(**features,task="transcribe",language="ru",do_sample=False,num_beams=1,max_new_tokens=170)
  t=processor.batch_decode(ids,skip_special_tokens=True)[0].strip()
  chunks.append({"start_s":start,"text":t,"token_count":len(tokens(t))})
  print("CHUNK",name,start,json.dumps(t,ensure_ascii=True)[:700],flush=True)
 texts[name]=chunks
def levenshtein(a,b):
 prev=list(range(len(b)+1))
 for i,x in enumerate(a,1):
  curr=[i]+[0]*len(b)
  for j,y in enumerate(b,1):curr[j]=min(prev[j]+1,curr[j-1]+1,prev[j-1]+(x!=y))
  prev=curr
 return prev[-1]
result={"source":texts["source_original_demucs_vocal"],
        "assessments":[],"speaker_identity_verified":False,"naturalness_verified":False,
        "asr_method":"Whisper small offline, on dry vocal source & converted 0-22 and 18-40, source-relative, affected by ASR errors"}
for key in ("candidate_12sec_reference","candidate_22sec_reference"):
 report=json.loads((D/("QA40_MyVoice_12secRef_40steps.quality.json" if "12sec" in key else "QA40_MyVoice_22secRef_40steps.quality.json")).read_text(encoding="utf-8"))
 count=0;edits=0;details=[]
 for src,dst in zip(texts["source_original_demucs_vocal"],texts[key]):
  a,b=tokens(src["text"]),tokens(dst["text"])
  d=levenshtein(a,b)
  count+=len(a);edits+=d
  details.append({"source_tokens":len(a),"converted_tokens":len(b),"edit_distance":d,"edit_fraction":round(d/max(1,len(a)),3)})
 item={
  "candidate":key,"reference_seconds":report["reference_preparation"]["seconds"],
  "reference_start_s":report["reference_preparation"]["start_seconds"],
  "model_cosine_proxy":report["speaker_embedding_cosine"],
  "missed_vocal_frame_ratio":report["voice_check"]["metrics"]["relative_missing_vocal_frames"],
  "vocal_dips":report["voice_check"]["metrics"]["energy_dip_events"],
  "asr_source_relative_edits":edits,"asr_source_tokens":count,
  "asr_edit_fraction":round(edits/max(1,count),3),
  "asr_chunks":details,"transcript":texts[key]}
 result["assessments"].append(item)
 print("QA40_COMPARISON",json.dumps({k:v for k,v in item.items() if k!="transcript"},ensure_ascii=True),flush=True)
(D/"QA40_ab_voice_asr_comparison.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
print("QA40_ASR_DONE",flush=True)
