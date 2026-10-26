"""QA70 objective CAMPPlus speaker reference comparison on identical 35s lead.
Proxy is one measure; cannot certify voice identity, quality, or smoothness.
"""
from pathlib import Path
import os,json,torch,numpy as np,soundfile as sf,torchaudio
R=Path.home()/"Music Studio";D=R/"Diagnostics"/"QA73";S=R/"Voice Engine"/"seed-vc"
os.chdir(S);os.environ["HF_HUB_CACHE"]=str(S/"checkpoints"/"hf_cache");os.environ["HF_HUB_OFFLINE"]="1"
import sys;sys.path.insert(0,str(S))
import torchaudio.compliance.kaldi as kaldi
from modules.campplus.DTDNN import CAMPPlus
from hf_utils import load_custom_model_from_hf
dev="cuda" if torch.cuda.is_available() else "cpu"
pth=load_custom_model_from_hf("funasr/campplus","campplus_cn_common.bin",config_filename=None)
model=CAMPPlus(feat_dim=80,embedding_size=192)
model.load_state_dict(torch.load(pth,map_location="cpu",weights_only=True))
model=model.eval().to(dev)
paths={
 "reference":R/"Diagnostics"/"QA57"/"reference_selected.wav",
 "source_original":R/"Diagnostics"/"QA54"/"QA54_CFG090_35s.source.wav",
 "QA67_continuous":R/"Diagnostics"/"QA67"/"QA67_ContinuousPhonemes_s95_Dry.wav",
 "QA54_personal":R/"Diagnostics"/"QA54"/"QA54_CFG090_35s.dry.wav"}
for c in json.loads((D/"qa73_timbre_transfer_report.json").read_text(encoding="utf-8"))["candidates"]:
 paths[c["name"]]=Path(c["dry"])
paths["QA70_prior_mic120"]=R/"Diagnostics"/"QA70"/"QA70_Mic120_Dyn55_Dry.wav"
def embed(path):
 arr,sr=sf.read(path,dtype="float32",always_2d=True)
 x=torch.from_numpy(arr.mean(axis=1).copy())
 if sr!=16000:x=torchaudio.functional.resample(x,sr,16000)
 x=x[:16000*25]
 feat=kaldi.fbank(x[None],num_mel_bins=80,dither=0,sample_frequency=16000)
 feat-=feat.mean(dim=0,keepdim=True)
 with torch.inference_mode():z=model(feat.unsqueeze(0).to(dev)).reshape(-1)
 return z
z={k:embed(p) for k,p in paths.items()}
vec=z["reference"]
metrics={k:round(float(torch.nn.functional.cosine_similarity(vec[None], v[None]).item()),4)
         for k,v in z.items() if k!="reference"}
(D/"qa73_speaker_metrics.json").write_text(json.dumps({"relative_to_user_reference":metrics,"model":"CAMPPlus","human_verified":False},ensure_ascii=False,indent=2),encoding="utf-8")
print("QA73_OWNER_VOICE_COSINE",json.dumps(metrics,ensure_ascii=True),flush=True)
