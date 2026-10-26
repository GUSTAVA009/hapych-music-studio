"""QA47 independent relative word preservation check, before publishing sample.
Uses same 18s windows as QA46 source and QA45 predecessor.
"""
import os,json,re,subprocess
from pathlib import Path
import numpy as np,soundfile as sf
R=Path.home()/"Music Studio";D=R/"Diagnostics"/"QA47"
base=R/"Diagnostics"/"QA46"/"QA46_comparison.json"
old=json.loads(base.read_text(encoding="utf-8"))
reference=old["source_text"]["original_source_vocal"]
previous=next(x for x in old["comparison"] if x["candidate"]=="qa45_previous")
raw=D/"plateau_13_sigma3.wav"
assert raw.is_file()
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
def tokens(t):return re.findall(r"[а-яё]+",t.casefold().replace("ё","е"))
def dist(a,b):
 prev=list(range(len(b)+1))
 for i,x in enumerate(a,1):
  row=[i]
  for j,y in enumerate(b,1):row.append(min(row[-1]+1,prev[j]+1,prev[j-1]+(x!=y)))
  prev=row
 return prev[-1]
spoken=[];parts=[]
for t,orig in zip((0,17),reference):
 byte=subprocess.run(["ffmpeg","-v","error","-nostdin","-ss",str(t),"-i",str(raw),
   "-t","18","-ac","1","-ar","16000","-f","f32le","pipe:1"],capture_output=True,check=True,timeout=90).stdout
 input=np.frombuffer(byte,dtype="<f4").copy()
 features=processor(input,sampling_rate=16000,return_tensors="pt",return_attention_mask=True)
 with torch.inference_mode():
  ids=model.generate(**features,task="transcribe",language="ru",do_sample=False,num_beams=1,max_new_tokens=150)
 pred=processor.batch_decode(ids,skip_special_tokens=True)[0]
 a,b=tokens(orig),tokens(pred)
 parts.append({"source_words":len(a),"out_words":len(b),"edit_distance":dist(a,b)})
 spoken.append(pred)
 print("QA47_TRANSCRIPT",t,json.dumps(pred,ensure_ascii=True)[:900],flush=True)
total=sum(v["source_words"] for v in parts)
error=sum(v["edit_distance"] for v in parts)/max(1,total)
report={"old_qa45_source_relative_word_error":previous["asr_relative_edits"],
 "new_qa47_source_relative_word_error":round(error,3),
 "transcripts":spoken,"segments":parts,
 "old_drop_events":previous["drop_events"],
 "new_drop_events":json.loads((D/"QA47_plateau_report.json").read_text(encoding="utf-8"))["selected"]["dips"],
 "phoneme_level_accuracy_verified":False,
 "human_accent_checked":False,
 "sample_accepted_for_listening":bool(error<=previous["asr_relative_edits"]+.05)}
(D/"QA47_relative_asr.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
print("QA47_ASR_RESULT",json.dumps({k:v for k,v in report.items() if k not in ("transcripts","segments")},ensure_ascii=True),flush=True)
