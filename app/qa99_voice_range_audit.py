"""QA99 compare F0 register/voicing of generated low baritone and same-seed
original Turbo using identical Demucs extraction and RMVPE.
No user tracks, voice references or trained models modified.
"""
from pathlib import Path
import json,os,sys
import numpy as np,soundfile as sf,torch
from scipy.signal import resample_poly
from math import gcd
R=Path.home()/'Music Studio';D=R/'Diagnostics'/'QA99-LowRegister'
S=R/'Voice Engine'/'seed-vc'
sys.path.insert(0,str(S));os.chdir(S)
os.environ['HF_HUB_CACHE']=str(S/'checkpoints'/'hf_cache');os.environ['HF_HUB_OFFLINE']='1'
from modules.rmvpe import RMVPE
from hf_utils import load_custom_model_from_hf
extractor=RMVPE(load_custom_model_from_hf('lj1995/VoiceConversionWebUI','rmvpe.pt',None),
 is_half=False,device=torch.device('cuda' if torch.cuda.is_available() else 'cpu'))
sources={
 'reference_Turbo_existing':R/'Diagnostics'/'QA86-SFTBenchmark'/'turbo_stems'/'htdemucs'/'turbo_35s'/'vocals.wav',
 'low_register_Turbo_new':D/'low_stems'/'htdemucs'/'qa99_lowbaritone_35s'/'vocals.wav',
 'SFT_reference':R/'Diagnostics'/'QA86-SFTBenchmark'/'sft_stems'/'htdemucs'/'sft_35s'/'vocals.wav'}
result={}
for name,path in sources.items():
 assert path.is_file(),path
 a,sr=sf.read(path,dtype='float32',always_2d=True);v=a.mean(axis=1)
 if sr!=16000:
  g=gcd(sr,16000);v=resample_poly(v,16000//g,sr//g)
 f0=np.asarray(extractor.infer_from_audio(v,thred=.03),dtype=float).ravel()
 voiced=f0[(f0>60)&(f0<700)]
 midi=69+12*np.log2(voiced/440)
 row={'voiced_frames':len(voiced),'voiced_fraction':round(len(voiced)/max(1,len(f0)),3),
   'median_hz':round(float(np.median(voiced)),2),
   'p15_hz':round(float(np.percentile(voiced,15)),2),
   'p85_hz':round(float(np.percentile(voiced,85)),2),
   'distance_from_user_median_semitones':round(float(12*np.log2(np.median(voiced)/120.8)),2),
   'above_190hz_fraction':round(float(np.mean(voiced>190)),3),
   'median_chromatic_cents_error':round(float(np.median(np.abs(midi-np.rint(midi)))*100),1),
   'p90_chromatic_cents_error':round(float(np.percentile(np.abs(midi-np.rint(midi)),90))*100,1),
   'not_a_voice_similarity_score':True}
 result[name]=row
 print('QA99_VOICE_RANGE',name,json.dumps(row,ensure_ascii=True),flush=True)
report={
 'experiment':'QA99 low bass baritone vs original Turbo',
 'same_song_text':True,'same_seed':7813095,'same_BPM':120,'same_duration_s':35,
 'source_path_changed_in_studio':False,'personal_voice_conversion_not_run':True,
 'quantitative':result,'speaker_timbre_not_verified':True}
(D/'qa99_voice_range_audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
