"""QA50 pre/post conversion phoneme-preservation audit (offline).
Music singing ASR may hallucinate or skip words: diagnostic, not certification.
"""
from pathlib import Path
import os,json,subprocess,re
import numpy as np
ROOT=Path.home()/"Music Studio";D=ROOT/"Diagnostics"/"QA54";D.mkdir(exist_ok=True,parents=True)
Q=ROOT/"Diagnostics"/"QA45"
paths={
"source_ACE":Q/"QA49_Overlap128_Soft_35s.source.wav",
"QA54_CFG040":ROOT/"Diagnostics"/"QA54"/"QA54_CFG040_35s.dry.wav",
"QA54_CFG090":ROOT/"Diagnostics"/"QA54"/"QA54_CFG090_35s.dry.wav",
"QA49":Q/"QA49_Overlap128_Soft_35s.dry.wav"}
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
def words(s):return re.findall(r"[а-яё]+",s.lower().replace("ё","е"))
results={}
for label,path in paths.items():
 records=[]
 for offset,duration in ((0,17),(17,18)):
  pcm=subprocess.run(["ffmpeg","-nostdin","-v","error","-ss",str(offset),"-i",str(path),"-t",str(duration),"-ar","16000","-ac","1","-f","f32le","pipe:1"],capture_output=True,check=True,timeout=60).stdout
  audio=np.frombuffer(pcm,dtype="<f4").copy()
  feat=proc(audio,sampling_rate=16000,return_tensors="pt",return_attention_mask=True)
  with torch.inference_mode():
   ids=model.generate(**feat,task="transcribe",language="ru",do_sample=False,num_beams=1,max_new_tokens=120)
  text=proc.batch_decode(ids,skip_special_tokens=True)[0]
  records.append({"start_s":offset,"text":text,"words":len(words(text))})
  print("QA54_SEGMENT",label,offset,json.dumps(text,ensure_ascii=True),flush=True)
 results[label]=records
(D/"qa54_source_vs_conversion_asr.json").write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding="utf-8")
