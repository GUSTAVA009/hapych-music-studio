"""QA130 independent post-conversion quality evaluation.
Lexical WER, pitch stability, dropout/jumps, owner similarity proxy.
No output is promoted to Music Studio without a human hearing check.
"""
from pathlib import Path
from math import gcd
import collections, hashlib,json,os,re,sys
os.environ.update(HF_HUB_OFFLINE="1",TRANSFORMERS_OFFLINE="1",TOKENIZERS_PARALLELISM="false")
import numpy as np, soundfile as sf, torch, torchaudio.compliance.kaldi as kaldi
from scipy.signal import resample_poly
from transformers import AutoProcessor,WhisperForConditionalGeneration,GenerationConfig
sys.stdout.reconfigure(encoding="utf-8")
torch.set_num_threads(4)
ROOT=Path.home()/"Music Studio"
D=ROOT/"Integrations"/"RussianOrthoepy"/"QA130-OwnerTimbre"
source=ROOT/"Integrations"/"OpenUtau-QA129"/"QA129_Score"/"QA129_Keiro_Russian_RealSinging_21s.wav"
ref=ROOT/"Мой голос"/"20261022_234327_Микрофон_3867cb.wav"
sidecar=json.loads((ROOT/"Integrations"/"OpenUtau-QA129"/"QA129_Score"/"QA129_phones.json").read_text(encoding="utf-8"))
transfer=json.loads((D/"qa130_transfer_report.json").read_text(encoding="utf-8"))
assert transfer["status"]=="rendered_pending_QA"
assert len(transfer["candidates"])==2
assert hashlib.sha256(source.read_bytes()).hexdigest()==transfer["source_sha256"]
S=ROOT/"Voice Engine"/"seed-vc"
os.chdir(S);sys.path.insert(0,str(S))
from hf_utils import load_custom_model_from_hf
from modules.campplus.DTDNN import CAMPPlus
from modules.rmvpe import RMVPE
def load16(path):
 a,sr=sf.read(path,always_2d=True,dtype="float32")
 a=a.mean(axis=1)
 if sr!=16000:
  g=gcd(sr,16000)
  a=resample_poly(a,16000//g,sr//g).astype("float32")
 return a
a_src=load16(source)
a_mic=load16(ref)
paths={"source":source}
for label,row in transfer["candidates"].items():
 assert row["status"]=="rendered"
 paths[label]=Path(row["filepath"])
 assert paths[label].is_file() and hashlib.sha256(paths[label].read_bytes()).hexdigest()==row["sha256"]
soulx_report=json.loads((ROOT/"Integrations"/"RussianOrthoepy"/"QA131-SoulX"/"qa131_run_report.json").read_text(encoding="utf-8"))
assert soulx_report["status"]=="rendered_pending_QA"
paths["soulx"]=Path(soulx_report["wav"])
assert hashlib.sha256(paths["soulx"].read_bytes()).hexdigest()==soulx_report["sha256"]
a={k:load16(p) for k,p in paths.items()}
for k,x in a.items():
 assert abs(len(x)/16000-20.88)<.07,(k,len(x))
# CAMPPlus similarity: a relative identity indicator, not perceptual confirmation.
sp=CAMPPlus(feat_dim=80,embedding_size=192)
sp.load_state_dict(torch.load(load_custom_model_from_hf("funasr/campplus","campplus_cn_common.bin",None),
                              map_location="cpu",weights_only=True))
sp.eval().to("cpu")
def embed(raw):
 hop=1600;k=len(raw)//hop*hop
 e=np.sqrt(np.mean(raw[:k].reshape(-1,hop).astype("float64")**2,axis=1)+1e-12)
 active=e>max(.0012,np.percentile(e,20)*1.18)
 wav=np.concatenate([raw[i*hop:(i+1)*hop] for i,b in enumerate(active) if b])
 if len(wav)<16000*4:
  # Some singing signals have unusually narrow dynamic range; preserve
  # original uninterrupted audio rather than reject or fabricate voiced spans.
  wav=raw.copy()
 assert len(wav)>16000*4
 wav=wav.copy();wav/=max(1e-6,float(np.sqrt(np.mean(wav.astype("float64")**2)))/.07)
 features=kaldi.fbank(torch.from_numpy(wav[None]),num_mel_bins=80,sample_frequency=16000,dither=0)
 features-=features.mean(0,keepdim=True)
 with torch.inference_mode():v=sp(features[None]).flatten().numpy()
 return v/np.linalg.norm(v)
owner_vector=np.load(ROOT/"Experiments"/"HAPYCH-HybridVoice"/"QA133-OwnerProfile"/"profile_embedding.npy")
owner_vector=owner_vector/np.linalg.norm(owner_vector)
emb={k:embed(y) for k,y in a.items()}
scores={k:round(float(v@owner_vector),4) for k,v in emb.items()}
# F0 comparison from RMVPE, consistent extraction for all candidates
rm=RMVPE(load_custom_model_from_hf("lj1995/VoiceConversionWebUI","rmvpe.pt",None),
 device=torch.device("cuda" if torch.cuda.is_available() else "cpu"),is_half=False)
f0={}
for k,y in a.items():
 f0[k]=np.asarray(rm.infer_from_audio(y,thred=.03),dtype="float64").ravel()
 print("QA130_F0_READY",k,len(f0[k]),flush=True)
def pitchdiff(out):
 sa=f0["source"];sb=f0[out];n=min(len(sa),len(sb))
 active=(sa[:n]>60)&(sb[:n]>60)&(sa[:n]<500)&(sb[:n]<500)
 dif=np.abs(1200*np.log2(sb[:n][active]/sa[:n][active]))
 if len(dif)<300:return {"active_frames":len(dif),"status":"insufficient"}
 return {"active_frames":len(dif),
   "median_abs_cents":round(float(np.median(dif)),2),
   "p90_abs_cents":round(float(np.percentile(dif,90)),2),
   "frac_above_70c":round(float(np.mean(dif>70)),4),
   "median_src_hz":round(float(np.median(sa[:n][active])),2),
   "median_out_hz":round(float(np.median(sb[:n][active])),2)}
# Acoustic safeguards compare active frames on source against candidate
hop=160
def env(y):
 n=len(y)//hop
 return np.sqrt(np.mean(y[:n*hop].reshape(-1,hop).astype("float64")**2,axis=1)+1e-12)
envs={k:env(v) for k,v in a.items()}
def acoustics(tag):
 e_src=envs["source"];e=envs[tag]
 n=min(len(e_src),len(e));e_src=e_src[:n];e=e[:n]
 active=e_src>max(.007,np.percentile(e_src,70)*.26)
 both=active & (e>.001)
 scale=np.median(e_src[both]/e[both])
 lost=active&(e*scale<e_src*.19)
 indices=np.flatnonzero(np.diff(np.r_[False,lost,False].astype(int)))
 long=[(round(i/100,2),round(j/100,2)) for i,j in zip(indices[::2],indices[1::2]) if j-i>=7]
 jumps=int(np.sum((abs(np.diff(np.log(e+1e-7)))>.9)&active[1:]))
 audio=a[tag]
 return {"active_source_frames":int(active.sum()),"source_rel_gain_db":round(20*np.log10(scale),2),
   "hard_dropouts_over70ms":len(long),"dropout_intervals":long[:10],
   "abrupt_level_jumps":jumps,
   "peak":round(float(np.max(np.abs(audio))),5),
   "clipped_sample_frac":round(float(np.mean(abs(audio)>.998)),6),
   "rms":round(float(np.sqrt(np.mean(audio.astype("float64")**2))),5)}
# Whisper-small can miss musical language. Compare per phrase and note that
# perfect WER is necessary here but insufficient for stress/timbre fidelity.
assets=ROOT/"Diagnostics"/"rejected-light-audit"/"whisper_text_assets"
weights=S/"checkpoints"/"hf_cache"/"models--openai--whisper-small"/"snapshots"/"973afd24965f72e36ca33b3055d56a652f456b4d"
proc=AutoProcessor.from_pretrained(str(assets),local_files_only=True)
asr=WhisperForConditionalGeneration.from_pretrained(str(weights),local_files_only=True,torch_dtype=torch.float32).eval()
asr.generation_config=GenerationConfig.from_pretrained(str(assets),local_files_only=True)
asr.generation_config.forced_decoder_ids=None;asr.config.forced_decoder_ids=None
def transcribe(y):
 inp=proc(y,sampling_rate=16000,return_tensors="pt",return_attention_mask=True)
 with torch.inference_mode():
  seq=asr.generate(**inp,language="ru",task="transcribe",do_sample=False,num_beams=1,max_new_tokens=150)
 return proc.batch_decode(seq,skip_special_tokens=True)[0]
def words(t):return re.findall("[а-яё]+",t.lower().replace("ё","е"))
def wer(exp,hyp):
 x=words(exp);z=words(hyp);r=list(range(len(z)+1))
 for v in x:
  q=[r[0]+1]
  for i,w in enumerate(z):q.append(min(q[-1]+1,r[i+1]+1,r[i]+int(v!=w)))
  r=q
 return round(r[-1]/max(1,len(x)),3)
expected=["Мне нужен свет твоих окон.","Меня услышишь и поймёшь.",
 "Когда за окном идёт дождь.","Сохрани мою любовь."]
groups=collections.defaultdict(list)
for s in sidecar["syllables"]:groups[s["line"]].append(s)
report={
 "stage":"QA130 auto-screen; owner identity and stress need listening",
 "source":{"file":str(source),"generated_voice":"Keiro Revenant from LUNAI Project",
  "licensed_scope":"noncommercial-only control; no model training","already_tested_line_WER":0.0},
 "owner_profile":"QA133 genuine mic profile; no synthetic references",
 "no_timbre_blend":True,"no_pitch_shift":True,"no_production_changes":True,
 "results":{},"human_approval_required":True}
for tag in ("consonant_safe","identity_focused","soulx"):
 y=a[tag];items=[]
 for i,sentence in enumerate(expected,1):
  start=round(groups[i][0]["tick"]*60/(102*480)*16000)
  end=round(((groups[i][-1]["tick"]+groups[i][-1]["duration_ticks"])*60/(102*480)+.38)*16000)
  output=transcribe(y[start:end])
  score=wer(sentence,output)
  items.append({"line":i,"expected":sentence,"recognized":output,"WER":score})
  print("QA130_ASR_LINE",tag,i,"WER",score,"TEXT",output,flush=True)
 whole=transcribe(y)
 pitch=pitchdiff(tag)
 audio=acoustics(tag)
 similarity=scores[tag]
 result={"word_error_lines":items,"mean_line_WER":round(sum(p["WER"] for p in items)/4,3),
    "full_whisper_transcript":whole,"full_WER":wer(" ".join(expected),whole),
    "owner_similarity_proxy":similarity,"source_owner_similarity_proxy":scores["source"],
    "similarity_gain_vs_source":round(similarity-scores["source"],4),
    "pitch":pitch,"audio":audio}
 pitch_ok=pitch.get("active_frames",0)>300 and pitch.get("median_abs_cents",1e9)<60 and pitch.get("p90_abs_cents",1e9)<110
 word_ok=all(item["WER"]==0.0 for item in items)
 audio_ok=audio["hard_dropouts_over70ms"]==0 and audio["clipped_sample_frac"]==0.0
 identity_gain=result["similarity_gain_vs_source"]>=0.03
 result["automated_gates"]={"words_exact_per_line":word_ok,
  "pitch_preservation":pitch_ok,"no_hard_dropouts_or_clipping":audio_ok,
  "identity_proxy_gain_at_least_0_03":identity_gain,
  "unverified_human_naturalness":False}
 result["not_approved_for_production"]=True
 report["results"][tag]=result
 (D/"QA130_quality_report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
 print("QA130_SCREEN",tag,json.dumps({"WER_lines":result["mean_line_WER"],
   "speaker_gain":result["similarity_gain_vs_source"],
   "pitch_median":pitch.get("median_abs_cents"),
   "dropouts":audio["hard_dropouts_over70ms"],"gates":result["automated_gates"]},ensure_ascii=False),flush=True)
print("QA130_QC_FINISHED",str(D/"QA130_quality_report.json"),flush=True)
