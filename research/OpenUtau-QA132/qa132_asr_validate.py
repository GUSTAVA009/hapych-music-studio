"""QA129 automated ASR screen on newly synthesized male Russian singing (not owner voice)."""
from pathlib import Path
from math import gcd
import os,json,re,sys,collections
os.environ.update(HF_HUB_OFFLINE="1",TRANSFORMERS_OFFLINE="1",TOKENIZERS_PARALLELISM="false")
import torch,numpy as np,soundfile as sf
from scipy.signal import resample_poly
from transformers import AutoProcessor,WhisperForConditionalGeneration,GenerationConfig
sys.stdout.reconfigure(encoding="utf-8")
torch.set_num_threads(2)
R=Path.home()/"Music Studio"
D=R/"Integrations"/"OpenUtau-QA129"/"QA132-KogdaPronunciation"
bank=R/"Voice Engine"/"seed-vc"/"checkpoints"/"hf_cache"/"models--openai--whisper-small"/"snapshots"/"973afd24965f72e36ca33b3055d56a652f456b4d"
assets=R/"Diagnostics"/"rejected-light-audit"/"whisper_text_assets"
p=AutoProcessor.from_pretrained(str(assets),local_files_only=True)
m=WhisperForConditionalGeneration.from_pretrained(str(bank),local_files_only=True,torch_dtype=torch.float32).eval()
m.generation_config=GenerationConfig.from_pretrained(str(assets),local_files_only=True)
m.generation_config.forced_decoder_ids=None;m.config.forced_decoder_ids=None
a,sr=sf.read(D/"QA132_RussianPronunciation_Corrected_21s.wav",always_2d=True,dtype="float32")
mono=a.mean(axis=1)
g=gcd(sr,16000)
mono=resample_poly(mono,16000//g,sr//g).astype("float32")
doc=json.loads((R/"Integrations"/"OpenUtau-QA129"/"QA129_Score"/"QA129_phones.json").read_text(encoding="utf-8"))
groups=collections.defaultdict(list)
for s in doc["syllables"]:groups[s["line"]].append(s)
def get_asr(x):
 inputs=p(x,sampling_rate=16000,return_tensors="pt",return_attention_mask=True)
 with torch.inference_mode():
  ids=m.generate(**inputs,language="ru",task="transcribe",do_sample=False,num_beams=1,max_new_tokens=100)
 return p.batch_decode(ids,skip_special_tokens=True)[0]
def words(t):return re.findall(r"[а-яё]+",t.lower().replace("ё","е"))
def edit(x,y):
 r=list(range(len(y)+1))
 for a in x:
  q=[r[0]+1]
  for j,b in enumerate(y):q.append(min(q[-1]+1,r[j+1]+1,r[j]+(a!=b)))
  r=q
 return r[-1]
expected=["Мне нужен свет твоих окон.","Меня услышишь и поймёшь.",
 "Когда за окном идёт дождь.","Сохрани мою любовь."]
results=[]
for i,text in enumerate(expected,1):
 samples=groups[i];start=samples[0]["tick"]*60/(102*480)
 end=(samples[-1]["tick"]+samples[-1]["duration_ticks"])*60/(102*480)+.4
 wave=mono[round(start*16000):round(end*16000)]
 recognized=get_asr(wave)
 err=round(edit(words(text),words(recognized))/len(words(text)),3)
 results.append({"line":i,"expected":text,"recognized":recognized,"WER":err})
 print("QA132_ASR_LINE",i,"WER",err,"TEXT",recognized,flush=True)
overall=get_asr(mono)
all_exp=words(" ".join(expected))
full_wer=round(edit(all_exp,words(overall))/len(all_exp),3)
out={"status":"ASR_checked_nonhuman",
 "engine":"Whisper-small Russian; may misrecognize synthesized singing",
 "full_track_transcript":overall,"full_track_word_error_rate":full_wer,
 "line_results":results,"expected_words":len(all_exp),
 "detected_keywords":{x:x in words(" ".join(r["recognized"] for r in results)) for x in ("окон","услышишь","поймешь","дождь","сохрани")},
 "manual_stress_hearing_required":True,
 "manual_voice_quality_hearing_required":True,
 "owner_voice_not_used":True,"production_music_studio_untouched":True}
(D/"QA132_asr_report.json").write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding="utf-8")
print("QA132_ASR_FINAL",json.dumps({"full_WER":full_wer,"keywords":out["detected_keywords"]},ensure_ascii=False),flush=True)
