"""QA39 A/B after prompt compiler fixes. Offline 28-second Russian Whisper-small
comparisons on dry original ACE-Step output, not studio-mixed files.
ASR is imperfect; do not present proxy accuracy as guaranteed diction.
"""
from pathlib import Path
import os,re,json,subprocess,difflib
import numpy as np,soundfile as sf
R=Path.home()/"Music Studio";D=R/"Diagnostics"/"QA42"
r=json.loads((R/"Diagnostics"/"QA38"/"request.json").read_text(encoding="utf-8"))
target=re.findall(r"[а-яё]+","\n".join(x for x in r["lyrics"].splitlines() if not x.strip().startswith("[")).lower().replace("ё","е"))
orig=list((R/"Diagnostics"/"QA39").glob("QA39_TURBO_corrected_same_seed.wav"))
new=list(D.glob("QA42_SungSource_160s_same_seed*.wav"))
assert len(orig)==len(new)==1,(orig,new)
files=[("QA39_SPOKEN_SOURCE",orig[0]),("QA42_160S_SUNG_SOURCE",new[0])]
os.environ.update(HF_HUB_OFFLINE="1",TRANSFORMERS_OFFLINE="1")
import torch
from transformers import AutoProcessor,WhisperForConditionalGeneration,GenerationConfig
torch.set_num_threads(3)
assets=R/"Diagnostics"/"rejected-light-audit"/"whisper_text_assets"
cache=R/"Voice Engine"/"seed-vc"/"checkpoints"/"hf_cache"/"models--openai--whisper-small"/"snapshots"/"973afd24965f72e36ca33b3055d56a652f456b4d"
p=AutoProcessor.from_pretrained(str(assets),local_files_only=True)
m=WhisperForConditionalGeneration.from_pretrained(str(cache),local_files_only=True,torch_dtype=torch.float32).eval()
m.generation_config=GenerationConfig.from_pretrained(str(assets),local_files_only=True)
m.generation_config.forced_decoder_ids=None;m.config.forced_decoder_ids=None
out=[]
for name,path in files:
 audio,sr=sf.read(str(path),dtype="float32",always_2d=True)
 segments=[]
 for t in [0,28,56,84,112,140]:
  z=subprocess.run(["ffmpeg","-nostdin","-v","error","-ss",str(t),"-i",str(path),"-t","28","-ac","1","-ar","16000","-f","f32le","pipe:1"],capture_output=True,check=True,timeout=60).stdout
  y=np.frombuffer(z,dtype="<f4").copy()
  if len(y)<16000*4:continue
  inputs=p(y,sampling_rate=16000,return_tensors="pt",return_attention_mask=True)
  with torch.inference_mode():tok=m.generate(**inputs,task="transcribe",language="ru",do_sample=False,num_beams=1,max_new_tokens=192)
  val=p.batch_decode(tok,skip_special_tokens=True)[0]
  segments.append({"start_s":t,"text":val})
 words=re.findall(r"[а-яё]+"," ".join(x["text"] for x in segments).lower().replace("ё","е"))
 sm=difflib.SequenceMatcher(None,target,words,autojunk=False)
 matches=sum(x.size for x in sm.get_matching_blocks())
 peak=float(np.max(np.abs(audio)))
 x={"candidate":name,"path":str(path),"seconds":round(len(audio)/sr,2),
    "target_words":len(target),"recognized_words":len(words),"matches_in_order":matches,
    "word_precision_proxy":round(matches/max(1,len(words)),3),
    "word_recall_proxy":round(matches/max(1,len(target)),3),
    "longest_consecutive_run":max((b.size for b in sm.get_matching_blocks()),default=0),
    "peak_dbfs":round(20*np.log10(max(1e-10,peak)),2),"segments":segments}
 out.append(x)
 print("QA42_ASR",json.dumps({k:v for k,v in x.items() if k!="segments"},ensure_ascii=True),flush=True)
(D/"QA42_sung_vs_spoken_asr.json").write_text(json.dumps(
 {"metrics_are_proxies_only":True,"method":"offline Whisper-small source audio A/B","results":out},ensure_ascii=False,indent=2),encoding="utf-8")
print("QA42_AB_COMPLETE",len(out),flush=True)
