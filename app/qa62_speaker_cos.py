"""QA62 independent CAMPPlus speaker embedding comparison on same user reference.
Same model as current QA54 reported cosine. Does not claim perceptual identity.
"""
import os,sys,json
from pathlib import Path
R=Path.home()/"Music Studio";D=R/"Diagnostics"/"QA62";S=R/"Voice Engine"/"seed-vc"
os.chdir(S);os.environ["HF_HUB_CACHE"]=str(S/"checkpoints"/"hf_cache");os.environ["HF_HUB_OFFLINE"]="1"
sys.path.insert(0,str(S))
import torch,numpy as np,soundfile as sf,torchaudio,torchaudio.compliance.kaldi as kaldi
from modules.campplus.DTDNN import CAMPPlus
from hf_utils import load_custom_model_from_hf
dev="cuda" if torch.cuda.is_available() else "cpu"
path=load_custom_model_from_hf("funasr/campplus","campplus_cn_common.bin",config_filename=None)
model=CAMPPlus(feat_dim=80,embedding_size=192)
model.load_state_dict(torch.load(path,map_location="cpu",weights_only=True))
model=model.eval().to(dev)
paths={"reference":R/"Diagnostics"/"QA57"/"reference_selected.wav",
 "source_singer":R/"Diagnostics"/"QA54"/"QA54_CFG090_35s.source.wav",
 "personal_QA54":R/"Diagnostics"/"QA54"/"QA54_CFG090_35s.dry.wav",
 "OpenVoice_t01":D/"QA62_OpenVoice_t01_raw.wav",
 "OpenVoice_t03":D/"QA62_OpenVoice_t03_raw.wav"}
def embed(p):
 audio,sr=sf.read(p,dtype="float32",always_2d=True)
 x=torch.from_numpy(audio.mean(axis=1).copy()).float()
 if sr!=16000:x=torchaudio.functional.resample(x,sr,16000)
 x=x[:16000*25]
 feat=kaldi.fbank(x[None,:],num_mel_bins=80,dither=0,sample_frequency=16000)
 feat=feat-feat.mean(dim=0,keepdim=True)
 with torch.no_grad():emb=model(feat[None,:,:].to(dev))
 return emb.reshape(-1)
vectors={k:embed(p) for k,p in paths.items()}
ref=vectors["reference"]
cos={k:round(float(torch.nn.functional.cosine_similarity(ref[None],v[None]).item()),4) for k,v in vectors.items() if k!="reference"}
result={"metric":"CAMPPlus cosine to user selected mic reference", "values":cos,
 "identity_human_verified":False,"directly_comparable_campplus_model":True,
 "voice_model_unchanged":True}
(D/"qa62_speaker_comparison.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
print("QA62_SPEAKER_COMPARE",json.dumps(result,ensure_ascii=True),flush=True)
