"""QA96 independent pitch fidelity and drop-outs for trained personal
SeedVC CFG0.4, CFG0.9 and CFG0.7/48-steps. Never alter studio or models.
"""
from pathlib import Path
import numpy as np,soundfile as sf,json,sys,os,torch
from scipy.signal import resample_poly
from math import gcd
R=Path.home()/'Music Studio';D=R/'Diagnostics'/'QA96-SmoothPersonal'
S=R/'Voice Engine'/'seed-vc'
sys.path.insert(0,str(R/'Voice Engine'))
from voice_guard42 import check as audio_check
sys.path.insert(0,str(S))
os.chdir(S)
os.environ['HF_HUB_CACHE']=str(S/'checkpoints'/'hf_cache');os.environ['HF_HUB_OFFLINE']='1'
from modules.rmvpe import RMVPE
from hf_utils import load_custom_model_from_hf
paths={
 'baseline_CFG040_step40':R/'Diagnostics'/'QA54'/'QA54_CFG040_35s.dry.wav',
 'baseline_CFG090_step40':R/'Diagnostics'/'QA54'/'QA54_CFG090_35s.dry.wav',
 'new_CFG070_step48':next((D/'cfg070_steps48').glob('vc_*.wav'))}
source=R/'Diagnostics'/'QA54'/'QA54_CFG090_35s.source.wav'
checkpoint=load_custom_model_from_hf('lj1995/VoiceConversionWebUI','rmvpe.pt',None)
extractor=RMVPE(checkpoint,is_half=False,device=torch.device('cuda' if torch.cuda.is_available() else 'cpu'))
def load_f0(path):
 y,sr=sf.read(path,dtype='float32',always_2d=True);x=y.mean(axis=1)
 if sr!=16000:
  g=gcd(sr,16000);x=resample_poly(x,16000//g,sr//g)
 return np.asarray(extractor.infer_from_audio(x,thred=.03),dtype='float64').ravel()
base=load_f0(source)
results={}
for label,path in paths.items():
 test=load_f0(path);n=min(len(base),len(test))
 f=base[:n];g=test[:n]
 mask=(f>55)&(f<1200)&(g>55)&(g<1200)
 error=1200*np.log2(g[mask]/f[mask])
 check=audio_check(source,path,D/(label+'.voicecheck.json'),'ru')
 pitch_jump_mask=mask[:-1]&mask[1:]&(abs(1200*np.log2(g[1:]/np.maximum(g[:-1],1e-9)))>75)&(abs(1200*np.log2(f[1:]/np.maximum(f[:-1],1e-9)))<30)
 s={'model':'alex_clean_qa44_v2','params':label,
   'median_absolute_pitch_error_cents':round(float(np.median(abs(error))),1),
   'p90_absolute_pitch_error_cents':round(float(np.percentile(abs(error),90)),1),
   'fraction_matched_pitch_gt35c':round(float(np.mean(abs(error)>35)),4),
   'fraction_matched_pitch_gt70c':round(float(np.mean(abs(error)>70)),4),
   'extra_jumps_10ms_over_75c':int(pitch_jump_mask.sum()),
   'matched_voiced_frames':int(mask.sum()),
   'source_voiced_missing_fraction':round(float(np.mean(~((g>55)&(g<1200))[(f>55)&(f<1200)])),4),
   'drop_frame_fraction':check.get('metrics',{}).get('relative_missing_vocal_frames'),
   'drop_events':check.get('metrics',{}).get('energy_dip_events'),
   'voice_check_status':check['status'],
   'voice_check_accepted':bool(check['accepted']),
   'speaker_identity_human_verified':False,
   'perceptual_naturalness_unverified':True}
 results[label]=s
 print('QA96_CENT_AUDIT',label,json.dumps(s,ensure_ascii=True),flush=True)
(D/'qa96_pitch_comparison.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf8')
