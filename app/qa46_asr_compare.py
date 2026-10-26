"""QA46 source-matched lyric/intelligibility comparison. Whisper-small local.
Do not treat Whisper as proof of human accent or exact phoneme correctness.
"""
from pathlib import Path
import re,os,json,subprocess
import numpy as np,soundfile as sf
from scipy.ndimage import gaussian_filter1d
R=Path.home()/"Music Studio";D=R/"Diagnostics"/"QA46";B=R/"Diagnostics"/"QA45"
files={
 "original_source_vocal":B/"QA45_MyVoice_QA44_35s.source.wav",
 "qa45_previous":B/"QA45_MyVoice_QA44_35s.dry.wav",
 "qa46_soft":D/"QA46_soft_QA45_verse_35s.dry.wav"}
assert all(x.is_file() for x in files.values()),files
os.environ.update(HF_HUB_OFFLINE="1",TRANSFORMERS_OFFLINE="1",HF_HUB_DISABLE_TELEMETRY="1")
import torch
from transformers import AutoProcessor,WhisperForConditionalGeneration,GenerationConfig
torch.set_num_threads(3)
assets=R/"Diagnostics"/"rejected-light-audit"/"whisper_text_assets"
cache=R/"Voice Engine"/"seed-vc"/"checkpoints"/"hf_cache"/"models--openai--whisper-small"/"snapshots"/"973afd24965f72e36ca33b3055d56a652f456b4d"
P=AutoProcessor.from_pretrained(str(assets),local_files_only=True)
M=WhisperForConditionalGeneration.from_pretrained(str(cache),local_files_only=True,torch_dtype=torch.float32).eval()
M.generation_config=GenerationConfig.from_pretrained(str(assets),local_files_only=True)
M.generation_config.forced_decoder_ids=None;M.config.forced_decoder_ids=None
def words(s):return re.findall(r"[а-яё]+",s.casefold().replace("ё","е"))
def ed(a,b):
 prev=list(range(len(b)+1))
 for i,x in enumerate(a,1):
  curr=[i]
  for j,y in enumerate(b,1):curr.append(min(curr[-1]+1,prev[j]+1,prev[j-1]+int(x!=y)))
  prev=curr
 return prev[-1]
def envelope_stats(file):
 x,sr=sf.read(file,dtype="float32",always_2d=True)
 x=x.mean(axis=1)
 hop=round(sr*.02)
 pad=(-len(x))%hop
 if pad:x=np.pad(x,(0,pad))
 f=x.reshape(-1,hop);rms=np.sqrt(np.mean(f.astype(float)**2,axis=1)+1e-12)
 d=20*np.log10(np.maximum(rms,1e-8));valid=rms>.008
 delta=np.diff(d)
 return {"rms_dynamic_10_to90_db":round(float(np.percentile(d[valid],90)-np.percentile(d[valid],10)),2),
 "loud_frame_step_over_3db":int(np.sum((np.abs(delta)>3)&valid[1:]&valid[:-1])),
 "high_frame_rms_pumping_db_95":round(float(np.percentile(np.abs(delta[valid[1:]&valid[:-1]]),95)),2)}
asr={}
for name,path in files.items():
 parts=[]
 for offset in (0,17):
  raw=subprocess.run(["ffmpeg","-v","error","-nostdin","-ss",str(offset),
   "-i",str(path),"-t","18","-ar","16000","-ac","1","-f","f32le","pipe:1"],
   check=True,capture_output=True,timeout=90).stdout
  y=np.frombuffer(raw,dtype="<f4").copy()
  inputs=P(y,sampling_rate=16000,return_tensors="pt",return_attention_mask=True)
  with torch.inference_mode():
   ids=M.generate(**inputs,task="transcribe",language="ru",do_sample=False,num_beams=1,max_new_tokens=140)
  t=P.batch_decode(ids,skip_special_tokens=True)[0]
  parts.append(t)
  print("QA46_ASR",name,offset,json.dumps(t,ensure_ascii=True)[:850],flush=True)
 asr[name]=parts
comparison=[]
for name in ("qa45_previous","qa46_soft"):
 ratios=[]
 for a,b in zip(asr["original_source_vocal"],asr[name]):
  q,s=words(a),words(b);ratios.append({"source_words":len(q),"out_words":len(s),"edits":ed(q,s)})
 edits=sum(x["edits"] for x in ratios);n=sum(x["source_words"] for x in ratios)
 folder=B if name=="qa45_previous" else D
 stem="QA45_MyVoice_QA44_35s" if name=="qa45_previous" else "QA46_soft_QA45_verse_35s"
 q=json.loads((folder/(stem+".quality.json")).read_text(encoding="utf-8"))
 v=q["voice_check"]["metrics"]
 item={"candidate":name,"asr_relative_edits":round(edits/max(1,n),3),"source_words":n,
  "speaker_cosine_proxy":q.get("speaker_embedding_cosine"),
  "drop_events":v.get("energy_dip_events"),"drop_max_seconds":v.get("longest_energy_dip_s"),
  "missed_vocal_frames":v.get("relative_missing_vocal_frames"),
  "gain_used":q.get("continuity"),"mixer":q.get("mix",{}).get("method"),
  "dynamic":envelope_stats(files[name]),"parts":ratios}
 comparison.append(item)
 print("QA46_METRICS",json.dumps({k:v for k,v in item.items() if k not in ("gain_used","parts")},ensure_ascii=True),flush=True)
(D/"QA46_comparison.json").write_text(json.dumps({
 "comparison":comparison,"source_text":asr,"accent_not_phonetically_certified":True,
 "source_audio_unmodified":True,"production_unmodified":True},ensure_ascii=False,indent=2),encoding="utf-8")
