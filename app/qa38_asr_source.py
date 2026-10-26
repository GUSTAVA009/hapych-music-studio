"""QA38 conservative audio screening of both freshly generated master tracks.
Whisper-small in offline CPU mode as a readability proxy, not artistic certification.
Outputs transcript+metrics and preserves source.
"""
from pathlib import Path
import os,json,re,time,subprocess,difflib
import numpy as np, soundfile as sf
from math import log10
ROOT=Path.home()/"Music Studio"
OUT=ROOT/"Diagnostics"/"QA38";OUT.mkdir(exist_ok=True,parents=True)
request=json.loads((OUT/"request.json").read_text(encoding="utf-8"))
files=sorted((ROOT/"Мои треки").glob("*QA38*.mp3"))
assert len(files)==2,(len(files),[f.name for f in files])
def russian_tokens(s):
 return re.findall(r"[а-яё]+",str(s).casefold().replace("ё","е"))
expected="\n".join(line for line in request["lyrics"].splitlines() if line.strip() and not line.lstrip().startswith("["))
target=russian_tokens(expected)
os.environ.update(HF_HUB_OFFLINE="1",TRANSFORMERS_OFFLINE="1",HF_HUB_DISABLE_TELEMETRY="1")
import torch
from transformers import AutoProcessor,WhisperForConditionalGeneration,GenerationConfig
torch.set_num_threads(3)
assets=ROOT/"Diagnostics"/"rejected-light-audit"/"whisper_text_assets"
cache=ROOT/"Voice Engine"/"seed-vc"/"checkpoints"/"hf_cache"/"models--openai--whisper-small"/"snapshots"/"973afd24965f72e36ca33b3055d56a652f456b4d"
processor=AutoProcessor.from_pretrained(str(assets),local_files_only=True)
model=WhisperForConditionalGeneration.from_pretrained(str(cache),local_files_only=True,torch_dtype=torch.float32).eval()
model.generation_config=GenerationConfig.from_pretrained(str(assets),local_files_only=True)
model.generation_config.forced_decoder_ids=None
model.config.forced_decoder_ids=None
results=[]
for p in files:
 print("QA38_ASR_BEGIN",p.name,flush=True)
 master=ROOT/"Мастер WAV"/(p.stem+".wav")
 assert master.is_file(),master
 audio,sr=sf.read(str(master),dtype="float32",always_2d=True)
 seconds=len(audio)/sr
 pieces=[]
 for offset in [0,28,56,84]:
  cmd=["ffmpeg","-v","error","-nostdin","-ss",str(offset),"-i",str(p),"-t","28","-ac","1","-ar","16000","-f","f32le","pipe:1"]
  output=subprocess.run(cmd,check=True,capture_output=True,timeout=60).stdout
  x=np.frombuffer(output,dtype="<f4").copy()
  if len(x)<16000*4:continue
  inputs=processor(x,sampling_rate=16000,return_tensors="pt",return_attention_mask=True)
  with torch.inference_mode():
   ids=model.generate(**inputs,task="transcribe",language="ru",do_sample=False,num_beams=1,max_new_tokens=192)
  spoken=processor.batch_decode(ids,skip_special_tokens=True)[0].strip()
  pieces.append({"start_s":offset,"text":spoken})
  print("ASR",p.stem[-14:],offset,json.dumps(spoken,ensure_ascii=True)[:800],flush=True)
 spoken=" ".join(part["text"] for part in pieces)
 tokens=russian_tokens(spoken)
 sm=difflib.SequenceMatcher(None,target,tokens,autojunk=False)
 matched=sum(m.size for m in sm.get_matching_blocks())
 precision=matched/max(1,len(tokens))
 recall=matched/max(1,len(target))
 consecutive_runs=[m.size for m in sm.get_matching_blocks() if m.size>0]
 repeated=(max([tokens.count(t) for t in set(tokens)],default=0)/max(1,len(tokens)))
 def db_rms(y):
  return round(20*log10(max(1e-10,float(np.sqrt(np.mean(np.square(y.astype("float64"))))))),2) if len(y) else -200
 def clip(s,e):
  return audio[max(0,int(s*sr)):min(len(audio),int(e*sr))]
 peak=round(20*log10(max(1e-10,float(np.max(np.abs(audio))))),2)
 r={"file":p.name,"duration_s":round(seconds,2),
    "source_expected_russian_words":len(target),"asr_russian_words":len(tokens),
    "matched_in_order":matched,"matched_precision":round(precision,3),
    "matched_recall":round(recall,3),"longest_recognized_order_run":max(consecutive_runs,default=0),
    "most_common_asr_word_fraction":round(repeated,3),
    "peak_dbfs":peak,
    "fade_head_dbfs":db_rms(clip(0,.4)),"fade_tail_dbfs":db_rms(clip(seconds-.4,seconds)),
    "intro_10s_dbfs":db_rms(clip(0,10)),"middle_40_to_85_dbfs":db_rms(clip(40,85)),
    "last_10s_dbfs":db_rms(clip(seconds-10,seconds)),
    "asr_segments":pieces,"has_nonzero_stereo":float(np.std(audio[:,0]-audio[:,1]))>.001,
    "caveat":"Whisper on sung music can mishear. Matched word ratio is a proxy, not WER or certified pronunciation."}
 print("QA38_EVAL",json.dumps({k:v for k,v in r.items() if k!="asr_segments"},ensure_ascii=True),flush=True)
 results.append(r)
 (OUT/"asr_mix_evaluation.json").write_text(json.dumps({"generated":True,"results":results},ensure_ascii=False,indent=2),encoding="utf-8")
print("QA38_ASR_FINISHED",len(results),flush=True)
