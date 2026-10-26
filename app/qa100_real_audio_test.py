"""Read-only QA100 on real QA54 (known audible mismatch)."""
from pathlib import Path
from math import gcd
import os,sys,json
import soundfile as sf,numpy as np,torch
from scipy.signal import resample_poly
R=Path.home()/'Music Studio';S=R/'Voice Engine'/'seed-vc'
sys.path.insert(0,str(S));os.chdir(S)
os.environ['HF_HUB_CACHE']=str(S/'checkpoints'/'hf_cache');os.environ['HF_HUB_OFFLINE']='1'
from modules.rmvpe import RMVPE
from hf_utils import load_custom_model_from_hf
from voice_intonation100 import measure
rm=RMVPE(load_custom_model_from_hf('lj1995/VoiceConversionWebUI','rmvpe.pt',None),
 is_half=False,device=torch.device('cuda' if torch.cuda.is_available() else 'cpu'))
def extract(p):
 x,sr=sf.read(p,always_2d=True,dtype='float32')
 x=x.mean(axis=1)
 if sr!=16000:
  g=gcd(sr,16000);x=resample_poly(x,16000//g,sr//g)
 return rm.infer_from_audio(x[:30*16000],thred=.03)
a=extract(R/'Diagnostics'/'QA54'/'QA54_CFG090_35s.source.wav')
b=extract(R/'Diagnostics'/'QA54'/'QA54_CFG090_35s.dry.wav')
report=measure(a,b)
assert report['status']=='review' and report['p90_abs_pitch_error_cents']>42
D=R/'Diagnostics'/'QA100-IntonationGuard';D.mkdir(parents=True,exist_ok=True)
(D/'qa100_real_voice_report.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf8')
print('QA100_REAL_TRACK_DETECTED',json.dumps(report,ensure_ascii=True),flush=True)
