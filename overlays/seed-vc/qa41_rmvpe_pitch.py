"""QA41 high-quality F0 diagnostics using the same RMVPE used for voice conversion.
No pitch manipulation or user-file changes. Samples kept local.
"""
import sys,json,time
from pathlib import Path
import numpy as np,librosa,soundfile as sf,torch
from scipy.ndimage import gaussian_filter1d
from scipy.signal import welch
HERE=Path(__file__).resolve().parent
R=HERE.parent.parent;Q=R/"Diagnostics"/"QA40";OUT=R/"Diagnostics"/"QA41"
sys.path.insert(0,str(HERE))
from hf_utils import load_custom_model_from_hf
from modules.rmvpe import RMVPE
torch.set_num_threads(3)
model_path=load_custom_model_from_hf("lj1995/VoiceConversionWebUI","rmvpe.pt",None)
ex=RMVPE(model_path,is_half=False,device=torch.device("cuda" if torch.cuda.is_available() else "cpu"))
files={"original":Q/"QA40_MyVoice_22secRef_40steps.source.wav",
       "vc12":Q/"QA40_MyVoice_12secRef_40steps.dry.wav",
       "vc22":Q/"QA40_MyVoice_22secRef_40steps.dry.wav"}
report=[]
for name,path in files.items():
 a,sr=sf.read(path,dtype="float32",always_2d=True)
 x=librosa.resample(a.mean(axis=1),orig_sr=sr,target_sr=16000)
 f0=np.asarray(ex.infer_from_audio(x,thred=.03),dtype=np.float64)
 valid=np.isfinite(f0)&(f0>65)&(f0<800)
 hz=f0.copy();hz[~valid]=0
 pitch=np.zeros_like(hz);pitch[valid]=69+12*np.log2(hz[valid]/440)
 jumps=np.abs(np.diff(pitch))>3
 jumpcount=int(np.sum(jumps&valid[:-1]&valid[1:]))
 # Analyse 'stationary melody' where a 1-second local contour fits within one semitone;
 # discard unvoiced intervals and note transitions to avoid labeling intended slides as vibrato.
 stable=np.zeros(len(pitch),bool)
 vibratos=[]
 window=100
 for t in range(0,len(f0)-window+1,50):
  section=pitch[t:t+window];v=valid[t:t+window]
  if v.mean()<.88:continue
  smooth=gaussian_filter1d(np.where(v,section,np.nanmedian(section[v])),sigma=10)
  if np.ptp(smooth)>1.0:continue
  delta=section-smooth
  z=(delta-np.mean(delta[v]))[v]
  rms=float(np.sqrt(np.mean(z*z)))
  freqs,power=welch(delta,fs=100,nperseg=100)
  region=(freqs>=4)&(freqs<=12)
  jitter=float(np.sqrt(np.trapz(power[region],freqs[region])))
  vibratos.append({"t":round(t/100,1),"fast_4to12hz_rms_semitones":round(jitter,3),
                   "contour_rms_semitones":round(rms,3)})
 median=float(np.median([w["fast_4to12hz_rms_semitones"] for w in vibratos])) if vibratos else None
 obs={"name":name,"voiced_fraction":round(float(valid.mean()),3),
      "median_hz":round(float(np.median(hz[valid])),1) if valid.any() else 0,
      "jump_over_3_semitones_adjacent_frames":jumpcount,
      "stable_windows_count":len(vibratos),
      "median_fast_pitch_modulation_semitones":round(median,3) if median is not None else None,
      "highest_modulated_stable_windows":sorted(vibratos,key=lambda w:w["fast_4to12hz_rms_semitones"],reverse=True)[:7]}
 report.append(obs)
 print("RMVPE_DIAGNOSTIC",json.dumps(obs,ensure_ascii=True),flush=True)
(OUT/"qa41_pitch_rmvpe.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
