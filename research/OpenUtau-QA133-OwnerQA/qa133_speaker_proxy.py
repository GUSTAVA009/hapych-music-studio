"""Relative CAMPPlus speaker-identity proxy (not a listening verdict).
The stored speaker centroid belongs to owner's own microphone recordings.
"""
from pathlib import Path
import os,sys,json,hashlib
from math import gcd
os.environ.update(CUDA_VISIBLE_DEVICES="-1",HF_HUB_OFFLINE="1",TRANSFORMERS_OFFLINE="1")
import torch,numpy as np,soundfile as sf
from scipy.signal import resample_poly
import torchaudio.compliance.kaldi as kaldi
sys.stdout.reconfigure(encoding="utf8")
torch.set_num_threads(2)
ROOT=Path.home()/"Music Studio"
S=ROOT/"Voice Engine"/"seed-vc"
os.chdir(S);sys.path.insert(0,str(S))
from hf_utils import load_custom_model_from_hf
from modules.campplus.DTDNN import CAMPPlus
D=ROOT/"Integrations"/"OpenUtau-QA129"/"QA132-KogdaPronunciation"/"QA133-FinalDiction"/"QA133-OwnerVoice"
report=json.loads((D/"QA133_owner_transfer.json").read_text(encoding="utf8"))
owner_vector=np.load(ROOT/"Experiments"/"HAPYCH-HybridVoice"/"QA133-OwnerProfile"/"profile_embedding.npy")
owner_vector=owner_vector/np.linalg.norm(owner_vector)
sp=CAMPPlus(feat_dim=80,embedding_size=192)
sp.load_state_dict(torch.load(load_custom_model_from_hf("funasr/campplus","campplus_cn_common.bin",None),
                               map_location="cpu",weights_only=True))
sp.eval().to("cpu")
def load16(path):
 a,sr=sf.read(path,always_2d=True,dtype="float32")
 a=a.mean(1)
 if sr!=16000:
  g=gcd(sr,16000)
  a=resample_poly(a,16000//g,sr//g).astype("float32")
 return a
def embed(raw):
 hop=1600
 n=len(raw)//hop
 e=np.sqrt(np.mean(raw[:n*hop].reshape(n,hop).astype("float64")**2,axis=1)+1e-12)
 active=e>max(.0012,float(np.percentile(e,20))*1.18)
 wav=np.concatenate([raw[i*hop:(i+1)*hop] for i,v in enumerate(active) if v])
 if len(wav)<16000*4:wav=raw.copy()
 wav=wav.copy()
 wav/=max(1e-6,float(np.sqrt(np.mean(wav.astype("float64")**2)))/.07)
 features=kaldi.fbank(torch.from_numpy(wav[None]),num_mel_bins=80,sample_frequency=16000,dither=0)
 features-=features.mean(0,keepdim=True)
 with torch.inference_mode():
  vector=sp(features[None]).flatten().numpy()
 return vector/np.linalg.norm(vector)
paths={"Keiro_source":Path(report["source"])}
for k,v in report["candidates"].items():paths[k]=Path(v["wav"])
old=ROOT/"Integrations"/"RussianOrthoepy"/"QA130-OwnerTimbre"/"QA130_MyVoice_identity_focused_21s.wav"
if old.exists():paths["old_QA130_identity"]=old
vals={}
for name,path in paths.items():
 similarity=round(float(embed(load16(path))@owner_vector),4)
 vals[name]=similarity
 print("QA133_OWNER_SIMILARITY_PROXY",name,similarity,flush=True)
out={"status":"relative_speaker_proxy_only","model":"CAMPPlus",
 "based_on_saved_owner_recording_centroid":True,
 "not_a_human_timbre_score":True,"cases":vals}
(D/"QA133_speaker_proxy.json").write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding="utf8")
