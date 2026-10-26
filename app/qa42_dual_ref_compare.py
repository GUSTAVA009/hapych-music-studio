"""QA42 dual-context experiment A/B quality gate, source-identical 40s.
Offline ASR as intelligibility proxy; no claims about naturalness/perceptual timbre.
"""
from pathlib import Path
import os,json,re,subprocess
import numpy as np
R=Path.home()/"Music Studio";D=R/"Diagnostics"/"QA42";Q=R/"Diagnostics"/"QA40"
src=Q/"QA40_MyVoice_22secRef_40steps.source.wav"
base=Q/"QA40_MyVoice_22secRef_40steps.dry.wav"
dual=D/"QA42_DualReference_40s_40steps.dry.wav"
paths={"source":src,"22s_style_22s_prompt":base,"22s_style_13s_prompt":dual}
assert all(p.is_file() for p in paths.values())
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
def tokens(x):return re.findall(r"[а-яё]+",x.casefold().replace("ё","е"))
def lev(a,b):
 prev=list(range(len(b)+1))
 for i,v in enumerate(a,1):
  nxt=[i]
  for j,w in enumerate(b,1):nxt.append(min(nxt[-1]+1,prev[j]+1,prev[j-1]+(v!=w)))
  prev=nxt
 return prev[-1]
texts={}
for name,path in paths.items():
 chunks=[]
 for start in (0,18):
  raw=subprocess.run(["ffmpeg","-nostdin","-v","error","-ss",str(start),"-i",str(path),
                      "-t","22","-ac","1","-ar","16000","-f","f32le","pipe:1"],
                     check=True,capture_output=True,timeout=90).stdout
  audio=np.frombuffer(raw,dtype="<f4").copy()
  inputs=processor(audio,sampling_rate=16000,return_tensors="pt",return_attention_mask=True)
  with torch.inference_mode():
   ids=model.generate(**inputs,task="transcribe",language="ru",do_sample=False,num_beams=1,max_new_tokens=150)
  chunks.append(processor.batch_decode(ids,skip_special_tokens=True)[0])
 texts[name]=chunks
result=[]
for name,reportfile in [("22s_style_22s_prompt",Q/"QA40_MyVoice_22secRef_40steps.quality.json"),
                        ("22s_style_13s_prompt",D/"QA42_DualReference_40s_40steps.quality.json")]:
 quality=json.loads(reportfile.read_text(encoding="utf-8"))
 per=[]
 for orig,candidate in zip(texts["source"],texts[name]):
  a,b=tokens(orig),tokens(candidate)
  per.append({"source_word_count":len(a),"converted_word_count":len(b),"edits":lev(a,b)})
 srcnum=sum(x["source_word_count"] for x in per);editnum=sum(x["edits"] for x in per)
 entry={"method":name,"reference_seconds":quality["reference_preparation"]["seconds"],
    "chunks":quality["stitching"]["diffusion_chunks"],"style_embedding_seconds":quality.get("reference_context42",{}).get("speaker_embedding_seconds"),
    "prompt_seconds":quality.get("reference_context42",{}).get("acoustic_prompt_seconds"),
    "speaker_embedding_cosine":quality.get("speaker_embedding_cosine"),
    "drop_ratio":quality["voice_check"]["metrics"]["relative_missing_vocal_frames"],
    "dip_events":quality["voice_check"]["metrics"]["energy_dip_events"],
    "pitch_status":quality.get("pitch_consistency",{}).get("status"),
    "relative_asr_edit":round(editnum/max(srcnum,1),3),"source_words":srcnum,
    "word_segments":per,"transcriptions":texts[name]}
 result.append(entry)
 print("QA42_DUAL_AB",json.dumps({k:v for k,v in entry.items() if k not in ("transcriptions","word_segments")},ensure_ascii=True),flush=True)
(D/"QA42_dual_ref_ab_report.json").write_text(json.dumps({"result":result,"method":"offline Whisper-small", "perceptual_voice_quality_verified":False},ensure_ascii=False,indent=2),encoding="utf-8")
