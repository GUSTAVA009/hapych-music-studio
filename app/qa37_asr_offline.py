"""QA37 Russian-lyrics intelligibility proxy on identical source vs A/B voice conversion.
Uses already-cached offline multilingual Whisper-small; no new downloads or user
data leaving machine. This is NOT accent, emotion or listener-quality certification.
"""
import os,json,re,subprocess,time
from pathlib import Path
import numpy as np
R=Path.home()/"Music Studio"
D=R/"Diagnostics"/"QA37"
src=R/"Diagnostics"/"QA36"/"QA36_calibration_original_40s.wav"
a=R/"Diagnostics"/"QA36"/"QA36_MY_VOICE_CALIBRATION_40s.mp3"
b=D/"QA37_B_REF3867_40s.mp3"
c=D/"QA37_C_23sec_ref_48steps.mp3"
d=D/"QA37_D_31sec_ref_40steps.mp3"
paths={"source_music_original":src,"converted_A_23sec":a,"converted_B_31sec":b,
       "converted_C_23sec_48steps":c,"converted_D_31sec_40steps":d}
assert all(p.is_file() for p in paths.values())
os.environ.update(HF_HUB_OFFLINE="1",TRANSFORMERS_OFFLINE="1",HF_HUB_DISABLE_TELEMETRY="1")
import torch
from transformers import AutoProcessor,WhisperForConditionalGeneration,GenerationConfig
import sys
sys.path.insert(0,str(R/'Voice Engine'))
from voice_guard24 import words,edit_distance
torch.set_num_threads(3)
assets=R/"Diagnostics"/"rejected-light-audit"/"whisper_text_assets"
cache=R/"Voice Engine"/"seed-vc"/"checkpoints"/"hf_cache"/"models--openai--whisper-small"/"snapshots"/"973afd24965f72e36ca33b3055d56a652f456b4d"
assert assets.is_dir() and cache.is_dir()
processor=AutoProcessor.from_pretrained(str(assets),local_files_only=True)
model=WhisperForConditionalGeneration.from_pretrained(str(cache),local_files_only=True,torch_dtype=torch.float32).eval()
model.generation_config=GenerationConfig.from_pretrained(str(assets),local_files_only=True)
model.generation_config.forced_decoder_ids=None;model.config.forced_decoder_ids=None
outputs={}
for name,p in paths.items():
 cmd=["ffmpeg","-v","error","-nostdin","-i",str(p),"-t","24","-ac","1","-ar","16000","-f","f32le","pipe:1"]
 data=subprocess.run(cmd,check=True,timeout=60,capture_output=True).stdout
 y=np.frombuffer(data,dtype="<f4").copy()
 ins=processor(y,sampling_rate=16000,return_tensors="pt",return_attention_mask=True)
 t0=time.monotonic()
 with torch.inference_mode():
  ids=model.generate(**ins,task="transcribe",language="ru",do_sample=False,num_beams=1,max_new_tokens=160)
 txt=processor.batch_decode(ids,skip_special_tokens=True)[0]
 outputs[name]={"text":txt,"word_count":len(words(txt)),"inference_seconds":round(time.monotonic()-t0,2)}
 print("TRANSCRIPT",name,json.dumps(outputs[name],ensure_ascii=True),flush=True)
base=words(outputs["source_music_original"]["text"])
for name in ["converted_A_23sec","converted_B_31sec","converted_C_23sec_48steps","converted_D_31sec_40steps"]:
 vals=words(outputs[name]["text"])
 dist=edit_distance(base,vals)
 outputs[name]["source_relative_word_edit"]=dist
 outputs[name]["source_relative_edit_fraction"]=round(dist/max(len(base),1),3)
print("METRICS",json.dumps({k:v.get("source_relative_edit_fraction") for k,v in outputs.items()},ensure_ascii=True),flush=True)
(D/"asr_offline_grid.json").write_text(json.dumps({"engine":"cached_whisper_small_ru",
    "interpretation":"Relative ASR differences of music mixtures, not verified lyric fidelity or accent",
    "region_seconds":24,"results":outputs},ensure_ascii=False,indent=2),encoding="utf-8")
