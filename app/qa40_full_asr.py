"""QA40 full-song linguistic preservation vs exact original QA39 source.
Uses cached local Whisper-small; gives proxy, not proof of native vocal/diction.
Does not alter audio.
"""
import os,json,re,subprocess,difflib
from pathlib import Path
import numpy as np
R=Path.home()/"Music Studio";D=R/"Diagnostics"/"QA40"
old=D.parent/"QA39"/"QA39_TURBO_corrected_same_seed.wav"
new=R/"Мастер WAV"/"QA40_Tikhiy_Svet_Full_22sRef_40steps.wav"
assert old.is_file() and new.is_file()
q=json.loads((D/"QA40_Tikhiy_Svet_Full_22sRef_40steps.quality.json").read_text(encoding="utf-8"))
os.environ.update(HF_HUB_OFFLINE="1",TRANSFORMERS_OFFLINE="1",HF_HUB_DISABLE_TELEMETRY="1")
import torch
from transformers import AutoProcessor,WhisperForConditionalGeneration,GenerationConfig
torch.set_num_threads(3)
assets=R/"Diagnostics"/"rejected-light-audit"/"whisper_text_assets"
cache=R/"Voice Engine"/"seed-vc"/"checkpoints"/"hf_cache"/"models--openai--whisper-small"/"snapshots"/"973afd24965f72e36ca33b3055d56a652f456b4d"
p=AutoProcessor.from_pretrained(str(assets),local_files_only=True)
model=WhisperForConditionalGeneration.from_pretrained(str(cache),local_files_only=True,torch_dtype=torch.float32).eval()
model.generation_config=GenerationConfig.from_pretrained(str(assets),local_files_only=True)
model.generation_config.forced_decoder_ids=None;model.config.forced_decoder_ids=None
def tokens(s):return re.findall(r"[а-яё]+",s.lower().replace("ё","е"))
def lev(a,b):
 prev=list(range(len(b)+1))
 for i,ai in enumerate(a,1):
  cur=[i]
  for j,bj in enumerate(b,1):cur.append(min(cur[-1]+1,prev[j]+1,prev[j-1]+(ai!=bj)))
  prev=cur
 return prev[-1]
results=[]
for start in [0,28,56,84]:
 row={"start_s":start}
 for name,source in [("original",old),("converted",new)]:
  cmd=["ffmpeg","-nostdin","-v","error","-ss",str(start),"-i",str(source),"-t","28","-ac","1","-ar","16000","-f","f32le","pipe:1"]
  raw=subprocess.run(cmd,capture_output=True,timeout=60,check=True).stdout
  x=np.frombuffer(raw,dtype="<f4").copy()
  features=p(x,sampling_rate=16000,return_tensors="pt",return_attention_mask=True)
  with torch.inference_mode():
   ids=model.generate(**features,task="transcribe",language="ru",do_sample=False,num_beams=1,max_new_tokens=192)
  row[name]=p.batch_decode(ids,skip_special_tokens=True)[0].strip()
 a,b=tokens(row["original"]),tokens(row["converted"])
 row["original_words"]=len(a);row["converted_words"]=len(b)
 row["relative_word_edit_distance"]=lev(a,b)
 row["relative_word_edit_fraction"]=round(lev(a,b)/max(1,len(a)),3)
 results.append(row)
 print("QA40_FULL_ASR_REGION",json.dumps({k:v for k,v in row.items() if k not in ("original","converted")},ensure_ascii=True),flush=True)
delta=sum(x["relative_word_edit_distance"] for x in results)
count=sum(x["original_words"] for x in results)
ratio=round(delta/max(1,count),3)
r={"full_audio_source":"QA39_TURBO_corrected_same_seed.wav",
 "full_audio_converted":str(new),"comparison_method":"Offline Whisper-small on four identical 28s music regions",
 "relative_asr_edit_ratio":ratio,"regions":results,
 "vocal_dips":q["voice_check"]["metrics"]["energy_dip_events"],
 "longest_vocal_dip_s":q["voice_check"]["metrics"]["longest_energy_dip_s"],
 "frame_loss_ratio":q["voice_check"]["metrics"]["relative_missing_vocal_frames"],
 "pitch_status":q.get("pitch_consistency",{}).get("status"),
 "speaker_cosine_proxy":q.get("speaker_embedding_cosine"),
 "recommended_to_promote":bool(ratio<.28 and q["voice_check"]["metrics"]["relative_missing_vocal_frames"]<.06),
 "human_quality_verified":False,"speaker_identity_verified":False,
 "caveat":"Singing music ASR contains many errors; this ratio is a proxy only."}
(D/"QA40_full_linguistic_qc.json").write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding="utf-8")
print("QA40_FULL_ASR_COMPLETE",json.dumps({k:v for k,v in r.items() if k!="regions"},ensure_ascii=True),flush=True)
