"""QA70: same-speaker consistency screen on local owner microphone takes.
Known approved speaker reference=QA57 22s, do not mix samples with low proxy.
"""
from pathlib import Path
import os,json,torch, numpy as np,soundfile as sf,torchaudio
R=Path.home()/"Music Studio";D=R/"Diagnostics"/"QA70";D.mkdir(parents=True,exist_ok=True)
S=R/"Voice Engine"/"seed-vc";os.chdir(S);os.environ["HF_HUB_CACHE"]=str(S/"checkpoints"/"hf_cache");os.environ["HF_HUB_OFFLINE"]="1"
import sys;sys.path.insert(0,str(S))
from modules.campplus.DTDNN import CAMPPlus
from hf_utils import load_custom_model_from_hf
import torchaudio.compliance.kaldi as kaldi
dev="cuda" if torch.cuda.is_available() else "cpu"
chk=load_custom_model_from_hf("funasr/campplus","campplus_cn_common.bin",config_filename=None)
model=CAMPPlus(feat_dim=80,embedding_size=192)
model.load_state_dict(torch.load(chk,map_location="cpu",weights_only=True))
model=model.eval().to(dev)
files=[R/"Diagnostics"/"QA57"/"reference_selected.wav",
   R/"Diagnostics"/"QA54"/"QA54_CFG090_35s.source.wav",
   R/"Diagnostics"/"QA54"/"QA54_CFG090_35s.dry.wav"]
files+=sorted((R/"Мой голос").glob("*.wav"))
def embed(p):
 a,sr=sf.read(p,dtype="float32",always_2d=True)
 x=torch.from_numpy(a.mean(axis=1).copy())
 if sr!=16000:x=torchaudio.functional.resample(x,sr,16000)
 x=x[:16000*25]
 e=kaldi.fbank(x[None],num_mel_bins=80,dither=0,sample_frequency=16000)
 e=e-e.mean(dim=0,keepdim=True)
 with torch.no_grad():z=model(e.unsqueeze(0).to(dev))
 return z.reshape(-1)
vec={p.name:embed(p) for p in files}
keys=list(vec)
matrix={}
for a in keys:
 matrix[a]={b:round(float(torch.nn.functional.cosine_similarity(vec[a][None],vec[b][None]).item()),4) for b in keys}
(D/"qa70_recording_speaker_consistency.json").write_text(json.dumps(matrix,ensure_ascii=False,indent=2),encoding="utf-8")
for key in keys:
 print("OWNER_RECORDING_COS",json.dumps({"name":key,"selected_ref":matrix[key][files[0].name],
     "qa54":matrix[key][files[2].name],"source":matrix[key][files[1].name]},ensure_ascii=True),flush=True)
