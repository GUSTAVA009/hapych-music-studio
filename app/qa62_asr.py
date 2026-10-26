"""QA59 apples-to-apples offline Russian lyric intelligibility screen.
Whisper-small cannot certify accent or syllable continuity; it is a coarse ASR guard.
"""
import os,json,re,subprocess,sys,difflib
from pathlib import Path
import numpy as np
R=Path.home()/"Music Studio";D=R/"Diagnostics"/"QA62";Q=R/"Diagnostics"/"QA54"
paths={
 "source_ACE":Q/"QA54_CFG090_35s.source.wav",
 "prior_QA54":Q/"QA54_CFG090_35s.dry.wav",
 "OpenVoice_tau010":D/"QA62_OpenVoice_t01_raw.wav",
 "OpenVoice_tau030":D/"QA62_OpenVoice_t03_raw.wav"}
assert all(p.is_file() for p in paths.values())
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
def tokens(s):return re.findall(r"[а-яё]+",s.casefold().replace("ё","е"))
def edits(a,b):
 previous=list(range(len(b)+1))
 for i,x in enumerate(a,1):
  now=[i]
  for j,y in enumerate(b,1):
   now.append(min(now[-1]+1,previous[j]+1,previous[j-1]+(x!=y)))
  previous=now
 return previous[-1]
windows=[(0,16),(16,19)]
trans={}
for label,p in paths.items():
 out=[]
 for start,duration in windows:
  pcm=subprocess.run(["ffmpeg","-nostdin","-v","error","-ss",str(start),"-i",str(p),
    "-t",str(duration),"-ar","16000","-ac","1","-f","f32le","pipe:1"],
    capture_output=True,check=True,timeout=90).stdout
  x=np.frombuffer(pcm,dtype="<f4").copy()
  features=proc(x,sampling_rate=16000,return_tensors="pt",return_attention_mask=True)
  with torch.inference_mode():
   predicted=model.generate(**features,task="transcribe",language="ru",do_sample=False,num_beams=1,max_new_tokens=180)
  text=proc.batch_decode(predicted,skip_special_tokens=True)[0]
  out.append({"start_s":start,"seconds":duration,"text":text,"n_words":len(tokens(text))})
  print("QA62_ASR",label,start,json.dumps(text,ensure_ascii=True)[:850],flush=True)
 trans[label]=out
target_words=["ладонях","окна","дороги","слова","торопить","тепло","горит","любить"]
report=[]
for label,rows in trans.items():
 if label=="source_ACE":continue
 n=0;e=0
 for a,b in zip(trans["source_ACE"],rows):
  t1=tokens(a["text"]);t2=tokens(b["text"])
  n+=len(t1);e+=edits(t1,t2)
 combined=[x for row in rows for x in tokens(row["text"])]
 markers={w:bool(w.replace("ё","е") in combined) for w in target_words}
 result={"model":label,"reference_word_count":n,"word_edit_count":e,
         "relative_asr_edit_fraction":round(e/max(1,n),3),
         "target_word_detected":markers,
         "target_word_detected_count":sum(markers.values()),
         "native_accent_verified":False,"uninterrupted_singing_verified":False}
 report.append(result)
 print("QA62_SCORES",json.dumps(result,ensure_ascii=True),flush=True)
(D/"qa62_asr_compare.json").write_text(json.dumps({"results":report,"asr":trans,
 "caution":"ASR song transcription may be wrong and does not measure syllable smoothness",
 "trained_voice_human_approved":False},ensure_ascii=False,indent=2),encoding="utf-8")
