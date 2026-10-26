"""QA43 comparative quality gate: same QA42 source vocal and personal Seed-VC result.
Offline Whisper-small on two 22s windows; only evaluates relative words, not
proof of accent or identity. Does not modify audio.
"""
from pathlib import Path
import os,json,re,subprocess
import numpy as np
R=Path.home()/"Music Studio"
D=R/"Diagnostics"/"QA43"
prefix="QA43_MyVoice_AltRef_22s_40steps"
paths={"source_qa42_vocal":D/(prefix+".source.wav"),
       "your_voice_conversion":D/(prefix+".dry.wav")}
if not all(f.is_file() for f in paths.values()):
 print("VOICE_NOT_READY",[str(v) for v in paths.values()],flush=True)
 raise SystemExit(4)
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
def words(s):return re.findall(r"[а-яё]+",s.casefold().replace("ё","е"))
def edits(a,b):
 previous=list(range(len(b)+1))
 for i,x in enumerate(a,1):
  current=[i]
  for j,y in enumerate(b,1):
   current.append(min(current[-1]+1,previous[j]+1,previous[j-1]+(x!=y)))
  previous=current
 return previous[-1]
texts={}
for name,path in paths.items():
 chunks=[]
 for start,duration in [(0,22),(18,22)]:
  command=["ffmpeg","-v","error","-nostdin","-ss",str(start),"-i",str(path),
           "-t",str(duration),"-ar","16000","-ac","1","-f","f32le","pipe:1"]
  pcm=subprocess.run(command,check=True,capture_output=True,timeout=60).stdout
  x=np.frombuffer(pcm,dtype="<f4").copy()
  inp=processor(x,sampling_rate=16000,return_tensors="pt",return_attention_mask=True)
  with torch.inference_mode():
   tok=model.generate(**inp,task="transcribe",language="ru",do_sample=False,num_beams=1,max_new_tokens=150)
  t=processor.batch_decode(tok,skip_special_tokens=True)[0]
  chunks.append({"start":start,"text":t,"words":len(words(t))})
  print("TRANSCRIPT",name,start,json.dumps(t,ensure_ascii=True)[:700],flush=True)
 texts[name]=chunks
sections=[]
for x,y in zip(texts["source_qa42_vocal"],texts["your_voice_conversion"]):
 a=words(x["text"]);b=words(y["text"])
 sections.append({"start_seconds":x["start"],"source_count":len(a),
                  "converted_count":len(b),"edit_distance":edits(a,b)})
count=sum(x["source_count"] for x in sections)
error=sum(x["edit_distance"] for x in sections)
q=json.loads((D/(prefix+".quality.json")).read_text(encoding="utf-8"))
guard=q.get("voice_check",{}).get("metrics",{})
result={"source_track":"QA42 - Тихий свет","reference":q["reference_preparation"]["source"],
 "reference_duration":q["reference_preparation"]["seconds"],"sample_start":35,
 "relative_asr_error":round(error/max(1,count),3),"source_tokens":count,
 "drop_fraction":guard.get("relative_missing_vocal_frames"),
 "dips":guard.get("energy_dip_events"),"max_dip_s":guard.get("longest_energy_dip_s"),
 "pitch_consistency":q.get("pitch_consistency",{}).get("status"),
 "speaker_similarity_proxy":q.get("speaker_embedding_cosine"),
 "lyrics_verified_by_listener":False,
 "natural_voice_verified_by_listener":False,
 "segments":sections,"transcripts":texts}
(D/"QA43_alt_compare_report.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
print("QA43_COMPARE",json.dumps({k:v for k,v in result.items() if k not in ("transcripts","segments")},ensure_ascii=True),flush=True)
