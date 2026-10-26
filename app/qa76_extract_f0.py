"""QA76 get stable 100Hz F0 from original ACE-step via RMVPE.
Used as a fixed melodic contour for experimental ApexSVC. Does not alter source audio.
"""
from pathlib import Path
import os,sys,json
import numpy as np,soundfile as sf
from scipy.signal import resample_poly
R=Path.home()/"Music Studio";D=R/"Diagnostics"/"QA76";D.mkdir(parents=True,exist_ok=True)
S=R/"Voice Engine"/"seed-vc"
os.environ["HF_HUB_CACHE"]=str(S/"checkpoints"/"hf_cache")
os.environ["HF_HUB_OFFLINE"]="1"
os.chdir(S);sys.path.insert(0,str(S))
import torch
from modules.rmvpe import RMVPE
from hf_utils import load_custom_model_from_hf
c=load_custom_model_from_hf("lj1995/VoiceConversionWebUI","rmvpe.pt",None)
model=RMVPE(c,is_half=False,device=torch.device("cuda" if torch.cuda.is_available() else "cpu"))
src=R/"Diagnostics"/"QA54"/"QA54_CFG090_35s.source.wav"
x,sr=sf.read(src,dtype="float32",always_2d=True)
assert sr==44100
v=resample_poly(x.mean(axis=1),160,441).astype(np.float32)
f=np.asarray(model.infer_from_audio(v,thred=.03),dtype=np.float64)
assert 3490<len(f)<3515,(len(f),len(v))
assert ((f>60)&(f<1000)).sum()>1800
np.save(D/"qa76_source_f0_rmvpe.npy",f.astype(np.float64),allow_pickle=False)
print("QA76_RMVPE_REFERENCE_READY",json.dumps({"frames":len(f),"voiced_frames":int(((f>60)&(f<1000)).sum()),"median_hz":round(float(np.median(f[f>60])),2),"min":round(float(f[f>60].min()),2),"max":round(float(f.max()),2)}),flush=True)
