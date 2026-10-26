"""QA62 independent voice-conversion architecture comparison: OpenVoiceV2 vs Seed-VC.
Target: same user's one microphone sample, same clean source singing, same song backing.
No user voice recordings outside this local machine, no learning, no production swap.
"""
import os,time,json,sys,hashlib,subprocess
from pathlib import Path
R=Path.home()/"Music Studio";D=R/"Diagnostics"/"QA62";D.mkdir(parents=True,exist_ok=True)
S=R/"Voice Engine"/"seed-vc"
os.environ["HF_HUB_CACHE"]=str(S/"checkpoints"/"hf_cache")
os.environ["HF_HUB_OFFLINE"]="1"
os.chdir(S);sys.path.insert(0,str(S));sys.path.insert(0,str(R/"Voice Engine"))
import torch,numpy as np,soundfile as sf
from scipy.signal import resample_poly
from modules.openvoice.api import ToneColorConverter
from studio_mix21 import vocal_room
from studio_mix16 import db
from studio_mix20 import power_frames
from voice_guard42 import check
src=R/"Diagnostics"/"QA54"/"QA54_CFG090_35s.source.wav"
tgt=R/"Diagnostics"/"QA57"/"reference_selected.wav"
q=json.loads((R/"Diagnostics"/"QA54"/"QA54_CFG090_35s.quality.json").read_text(encoding="utf-8"))
input_audio,sr=sf.read(src,dtype="float32",always_2d=True)
reference,ref_sr=sf.read(tgt,dtype="float32",always_2d=True)
previous,p_sr=sf.read(R/"Diagnostics"/"QA54"/"QA54_CFG090_35s.finished.wav",dtype="float32",always_2d=True)
mix,m_sr=sf.read(q["master"],dtype="float32",always_2d=True)
assert sr==ref_sr==p_sr==m_sr==44100
sr_model=22050
a=resample_poly(input_audio.mean(axis=1),1,2).astype("float32")
b=resample_poly(reference.mean(axis=1),1,2).astype("float32")
device="cuda" if torch.cuda.is_available() else "cpu"
model_dir=S/"checkpoints"/"models--myshell-ai--OpenVoiceV2"/"snapshots"/"f36e7edfe1684461a8343844af60babc2efbb727"/"converter"
ck=model_dir/"checkpoint.pth";cfg=model_dir/"config.json"
assert ck.is_file() and cfg.is_file()
model=ToneColorConverter(str(cfg),device=device)
model.load_ckpt(str(ck))
input_tensor=torch.tensor(a,device=device).unsqueeze(0)
ref_tensor=torch.tensor(b,device=device).unsqueeze(0)
with torch.inference_mode():
 se_src=model.extract_se(input_tensor,torch.LongTensor([input_tensor.shape[-1]]).to(device))
 se_tgt=model.extract_se(ref_tensor,torch.LongTensor([ref_tensor.shape[-1]]).to(device))
se_cos=float(torch.nn.functional.cosine_similarity(se_src.flatten()[None],se_tgt.flatten()[None]).item())
n=len(mix);saved=[]
gain=10**(float(q["mix"]["master_gain_db"])/20)
old=np.pad(previous.mean(axis=1),(0,max(0,n-len(previous))))[:n]
music=mix/gain-vocal_room(old,sr)
original=np.pad(input_audio.mean(axis=1),(0,max(0,n-len(input_audio))))[:n]
for tau in (0.10,0.30):
 start=time.monotonic()
 with torch.inference_mode():
  converted=model.convert(input_tensor,torch.LongTensor([len(a)]).to(device),
                          se_src,se_tgt,tau=tau)
 v=converted.detach().float().cpu().numpy().reshape(-1)
 x=resample_poly(v,2,1).astype("float32")
 if len(x)<n:x=np.pad(x,(0,n-len(x)))
 elif len(x)>n:x=x[:n]
 tag=str(tau).replace(".","")
 raw=D/("QA62_OpenVoice_t"+tag+"_raw.wav")
 sf.write(raw,x,sr,subtype="FLOAT")
 check_result=check(src,raw,D/("qa62_integrity_t"+tag+".json"),"ru")
 hop=sr//100
 r=power_frames(original,hop);s=power_frames(x,hop)
 active=(r>max(10**(-48/20),float(np.percentile(r,85))*.15))&(s>10**(-55/20))
 assert active.sum()>20
 change=float(np.clip(np.median(db(r[active])-db(s[active])),-16,18))
 processed=x*(10**(change/20))
 y=(music+vocal_room(processed,sr))*gain
 p=float(np.max(abs(y)));y*=min(1.0,.89/max(p,1e-7))
 wav=D/("QA62_OpenVoice_t"+tag+"_Mix_24bit.wav")
 mp3=D/("QA62_OpenVoice_t"+tag+"_35s_320kbps.mp3")
 sf.write(wav,y,sr,subtype="PCM_24")
 p=subprocess.run(["ffmpeg","-nostdin","-v","error","-y","-i",str(wav),
                   "-c:a","libmp3lame","-b:a","320k",str(mp3)],capture_output=True,text=True,timeout=120)
 assert p.returncode==0,p.stderr[-1000:]
 item={"tau":tau,"time_s":round(time.monotonic()-start,1),
       "ref_embed_cosine":round(se_cos,4),"length_s":round(len(y)/sr,3),
       "vocal_loss":check_result["metrics"]["relative_missing_vocal_frames"],
       "drop_events":check_result["metrics"]["energy_dip_events"],
       "max_drop_s":check_result["metrics"]["longest_energy_dip_s"],
       "global_vocal_gain_db":round(change,2),"file":str(mp3),
       "source_and_user_ref_only":True,"production_unchanged":True,
       "natural_singing_not_verified":True}
 saved.append(item)
 print("QA62_OPENVOICE_CANDIDATE",json.dumps(item,ensure_ascii=True),flush=True)
 (D/"qa62_results.json").write_text(json.dumps(saved,ensure_ascii=False,indent=2),encoding="utf-8")
print("QA62_ALTERNATIVE_MODEL_READY",len(saved),flush=True)
