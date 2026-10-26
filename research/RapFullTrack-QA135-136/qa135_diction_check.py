"""Compare lexical intelligibility of the original separated vocals and
the QA133 consonant-protection voice transfer. Whisper-small local CPU only.
This is NOT a human accent/timbre assessment and is not used to rewrite audio.
"""
from pathlib import Path
from math import gcd
import json,os,sys,re
from difflib import SequenceMatcher
os.environ.update(HF_HUB_OFFLINE="1",TRANSFORMERS_OFFLINE="1",TOKENIZERS_PARALLELISM="false")
import numpy as np,soundfile as sf,torch
from scipy.signal import resample_poly
from transformers import AutoProcessor,WhisperForConditionalGeneration,GenerationConfig
sys.stdout.reconfigure(encoding="utf8")
torch.set_num_threads(3)
R=Path.home()/"Music Studio"
D=R/"Integrations"/"RapFullTrack-QA135"
quality=json.loads((D/"QA135_final_report.json").read_text(encoding="utf8"))
vocal=Path(json.loads((D/"Results"/"QA135_apex_pipeline_report.json").read_text(encoding="utf8"))["vocal_stem_file"])
converted=Path(json.loads((D/"Results"/"QA135_apex_pipeline_report.json").read_text(encoding="utf8"))["dry_vocal"])
assert vocal.is_file() and converted.is_file()
assets=R/"Diagnostics"/"rejected-light-audit"/"whisper_text_assets"
weights=R/"Voice Engine"/"seed-vc"/"checkpoints"/"hf_cache"/"models--openai--whisper-small"/"snapshots"/"973afd24965f72e36ca33b3055d56a652f456b4d"
proc=AutoProcessor.from_pretrained(str(assets),local_files_only=True)
model=WhisperForConditionalGeneration.from_pretrained(str(weights),local_files_only=True,torch_dtype=torch.float32).eval()
model.generation_config=GenerationConfig.from_pretrained(str(assets),local_files_only=True)
model.generation_config.forced_decoder_ids=None;model.config.forced_decoder_ids=None
def load(path):
 a,sr=sf.read(path,dtype="float32",always_2d=True)
 a=a.mean(axis=1)
 if sr!=16000:
  g=gcd(sr,16000);a=resample_poly(a,16000//g,sr//g).astype("float32")
 return a
def get_text(audio):
 i=proc(audio,sampling_rate=16000,return_tensors="pt",return_attention_mask=True)
 with torch.inference_mode():
  generated=model.generate(**i,language="ru",task="transcribe",do_sample=False,num_beams=1,max_new_tokens=128)
 return proc.batch_decode(generated,skip_special_tokens=True)[0].strip()
def words(text):
 return re.findall(r"[а-яё]+",text.lower().replace("ё","е"))
src=load(vocal);out=load(converted)
n=min(len(src),len(out))
assert n>16000*145
segments=[(float(i),float(min(i+24,150.65))) for i in range(0,150,24)]
results={}
for name,a in (("source_singer",src),("owner_qa133_consonants",out)):
 lines=[]
 for start,end in segments:
  clip=a[round(start*16000):round(end*16000)]
  text=get_text(clip)
  lines.append({"seconds":[start,end],"transcript":text})
  print("QA135_ASR",name,start,text[:175],flush=True)
 joined=" ".join(item["transcript"] for item in lines)
 results[name]={"segments":lines,"transcript":joined,"words":len(words(joined))}
new=words(results["owner_qa133_consonants"]["transcript"])
old=words(results["source_singer"]["transcript"])
ratio=float(SequenceMatcher(None,old,new,autojunk=False).ratio())
# Lexical loss is approximate because independent ASR can change
# wording on identical waveforms, especially with overlapping segments.
results["comparison"]={
 "source_vs_converted_token_sequence_similarity":round(ratio,3),
 "lexical_retention_is_approximate":True,
 "not_proof_all_lyrics_were_sung":True,
 "not_proof_correct_stress_or_timbre":True,
 "source_recognized_tokens":len(old),
 "converted_recognized_tokens":len(new)}
(D/"QA135_diction_comparison.json").write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding="utf8")
print("QA135_ASR_FINISHED",results["comparison"],flush=True)
