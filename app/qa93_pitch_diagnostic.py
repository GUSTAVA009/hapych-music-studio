"""QA93 diagnostics: cents drift from exact pitch, and relative F0 drift of
voice converters vs original SFT voice. Read-only, local, 35-second samples.
No changes to model, user's voice samples, or working Music Studio.
"""
from pathlib import Path
import sys,os,time,json
import numpy as np,soundfile as sf
from scipy.signal import resample_poly
from scipy.ndimage import median_filter,gaussian_filter1d
from math import gcd
R=Path.home()/'Music Studio';D=R/'Diagnostics'/'QA93-Intonation'
D.mkdir(parents=True,exist_ok=True)
S=R/'Voice Engine'/'seed-vc'
os.environ['HF_HUB_CACHE']=str(S/'checkpoints'/'hf_cache')
os.environ['HF_HUB_OFFLINE']='1'
os.chdir(S);sys.path.insert(0,str(S))
import torch
from modules.rmvpe import RMVPE
from hf_utils import load_custom_model_from_hf
checkpoint=load_custom_model_from_hf('lj1995/VoiceConversionWebUI','rmvpe.pt',None)
rmvpe=RMVPE(checkpoint,is_half=False,device=torch.device('cuda' if torch.cuda.is_available() else 'cpu'))
files={
 'SFT_source':R/'Diagnostics'/'QA86-SFTBenchmark'/'sft_stems'/'htdemucs'/'sft_35s'/'vocals.wav',
 'QA89_cfg2':R/'Diagnostics'/'QA89-SFTPersonal'/'run_svc_28steps_cfg20'/'generated.wav',
 'QA91_gentle':R/'Diagnostics'/'QA91-SmoothIdentity'/'gentle12'/'generated.wav',
 'QA91_balanced':R/'Diagnostics'/'QA91-SmoothIdentity'/'balanced16'/'generated.wav'}
f0={}
for label,p in files.items():
 assert p.exists()
 x,sr=sf.read(p,always_2d=True,dtype='float32')
 y=x.mean(axis=1)
 if sr!=16000:
  g=gcd(sr,16000);y=resample_poly(y,16000//g,sr//g)
 pitch=np.asarray(rmvpe.infer_from_audio(y,thred=.03),dtype='float32').ravel()
 f0[label]=pitch
 np.save(D/(label+'_f0_100hz.npy'),pitch)
 print('F0_READ',label,pitch.size,'voiced',float(np.mean(pitch>55)),flush=True)
src=f0['SFT_source']
results={}
for label,obs in f0.items():
 n=min(len(src),len(obs));s=src[:n];o=obs[:n]
 valid=(s>55)&(s<1200)&(o>55)&(o<1200)
 midiS=np.zeros(n);midiO=np.zeros(n)
 midiS[s>55]=69+12*np.log2(s[s>55]/440)
 midiO[o>55]=69+12*np.log2(o[o>55]/440)
 delta=(midiO-midioS) if False else midiO-midiS
 v=valid & (np.abs(delta)<2)
 deviations=np.abs(delta[v])*100 if v.any() else np.array([])
 # Stable note windows 130ms where local range <80c; excludes many glides.
 ms=median_filter(midiS,size=13)
 window_var=np.abs(midiS-ms)
 stable=valid&(window_var<.18)
 # Only take voiced notes longer than 120 ms with low pitch drift.
 stable &= (np.abs(gaussian_filter1d(midiS,sigma=3)-midiS)<.18)
 cents=midiO[stable]-midiS[stable]
 nearS=np.abs((midiS[stable]-np.rint(midiS[stable])))*100
 nearO=np.abs((midiO[stable]-np.rint(midiO[stable])))*100
 row={
 'duration_s':round(n/100,2),'matched_voiced_frames':int(valid.sum()),
 'stable_matched_frames':int(stable.sum()),
 'source_relative_median_cents':round(float(np.median(cents))*100,2) if len(cents) else None,
 'source_relative_median_absolute_cents':round(float(np.median(np.abs(cents)))*100,2) if len(cents) else None,
 'source_relative_p90_absolute_cents':round(float(np.percentile(np.abs(cents),90))*100,2) if len(cents) else None,
 'source_relative_fraction_gt25c':round(float(np.mean(np.abs(cents)>0.25)),4) if len(cents) else None,
 'source_relative_fraction_gt40c':round(float(np.mean(np.abs(cents)>0.4)),4) if len(cents) else None,
 'source_stable_note_median_from_equal_temperament_cents':round(float(np.median(nearS)),2) if len(nearS) else None,
 'output_stable_note_median_from_equal_temperament_cents':round(float(np.median(nearO)),2) if len(nearO) else None,
 'source_stable_note_p90_from_equal_temperament_cents':round(float(np.percentile(nearS,90)),2) if len(nearS) else None,
 'output_stable_note_p90_from_equal_temperament_cents':round(float(np.percentile(nearO,90)),2) if len(nearO) else None,
 'source_model_fidelity_only':True,'cannot_verify_key_or_artistic_interval':True}
 results[label]=row
 print('QA93_PITCH',label,json.dumps(row,ensure_ascii=True),flush=True)
(D/'qa93_pitch_report.json').write_text(json.dumps(results,indent=2,ensure_ascii=False),encoding='utf8')
